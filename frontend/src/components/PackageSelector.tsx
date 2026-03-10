import { useState, useEffect } from 'react';
import {
  Card, Input, InputNumber, DatePicker, Button, Tabs, Space, Empty,
  message, Spin, Tag, Modal, Drawer, Typography, Popconfirm
} from 'antd';
import {
  PlusOutlined, EditOutlined, RobotOutlined, AppstoreOutlined, DeleteOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getPackageGroups, createMenuFromPackage, aiCreatePackage,
  createPackageGroup, createPackage, deletePackage,
} from '../api/menuApi';
import type { PackageGroup, MenuData, User } from '../api/menuApi';
import PackageTemplateEditor from './PackageTemplateEditor';

const { Text, Title } = Typography;

interface Props {
  user: User;
  onMenuCreated: (menu: MenuData) => void;
  loading: boolean;
  setLoading: (v: boolean) => void;
}

export default function PackageSelector({ user, onMenuCreated, loading, setLoading }: Props) {
  const [groups, setGroups] = useState<PackageGroup[]>([]);
  const [customerName, setCustomerName] = useState('');
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [partySize, setPartySize] = useState(10);
  const [tableCount, setTableCount] = useState(1);
  const [fetchingGroups, setFetchingGroups] = useState(false);

  // 模板编辑
  const [editingPackageId, setEditingPackageId] = useState<number | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  // 新建分组
  const [newGroupModalOpen, setNewGroupModalOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');

  // AI 创建
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiDescription, setAiDescription] = useState('');
  const [aiGroupId, setAiGroupId] = useState<number | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const fetchGroups = async () => {
    setFetchingGroups(true);
    try {
      const data = await getPackageGroups();
      setGroups(data);
    } catch (e: any) {
      message.error(e.message || '加载套餐失败');
    } finally {
      setFetchingGroups(false);
    }
  };

  useEffect(() => { fetchGroups(); }, []);

  const handleSelectPackage = async (packageId: number) => {
    if (!customerName.trim()) {
      message.warning('请填写客户名');
      return;
    }
    setLoading(true);
    try {
      const menu = await createMenuFromPackage({
        customer_name: customerName.trim(),
        date,
        party_size: partySize,
        table_count: tableCount,
        package_id: packageId,
      });
      onMenuCreated(menu);
      message.success('菜单已创建');
    } catch (e: any) {
      message.error(e.message || '创建菜单失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) return;
    try {
      await createPackageGroup(newGroupName.trim());
      setNewGroupModalOpen(false);
      setNewGroupName('');
      fetchGroups();
      message.success('分组已创建');
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleAICreate = async () => {
    if (!aiDescription.trim() || !aiGroupId) return;
    setAiLoading(true);
    try {
      const result = await aiCreatePackage(aiDescription.trim(), aiGroupId);
      message.success(`AI 套餐「${result.name}」已创建`);
      setAiModalOpen(false);
      setAiDescription('');
      fetchGroups();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleNewEmptyPackage = async (groupId: number) => {
    const name = `新套餐 ${dayjs().format('MM-DD HH:mm')}`;
    try {
      const result = await createPackage({ group_id: groupId, name });
      message.success('空套餐已创建，请编辑');
      setEditingPackageId(result.id);
      setEditorOpen(true);
      fetchGroups();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeletePackage = async (packageId: number, packageName: string) => {
    try {
      await deletePackage(packageId);
      message.success(`套餐「${packageName}」已删除`);
      await fetchGroups();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const tabItems = groups.map((group) => ({
    key: String(group.id),
    label: group.name,
    children: (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, padding: '8px 0' }}>
        {group.packages.length === 0 && (
          <Empty description="暂无套餐" style={{ margin: '40px auto' }}>
            <Space>
              <Button onClick={() => handleNewEmptyPackage(group.id)}>手动新建</Button>
              <Button icon={<RobotOutlined />} onClick={() => { setAiGroupId(group.id); setAiModalOpen(true); }}>
                AI 生成
              </Button>
            </Space>
          </Empty>
        )}
        {group.packages.map((pkg) => (
          <Card
            key={pkg.id}
            hoverable
            style={{ width: 220, position: 'relative' }}
            styles={{ body: { padding: 16 } }}
            onClick={() => handleSelectPackage(pkg.id)}
          >
            <div
              style={{ position: 'absolute', top: 8, right: 8 }}
              onClick={(e) => e.stopPropagation()}
            >
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  setEditingPackageId(pkg.id);
                  setEditorOpen(true);
                }}
              />
              <Popconfirm
                title="确认删除这个套餐？"
                okText="删除"
                cancelText="取消"
                onConfirm={() => handleDeletePackage(pkg.id, pkg.name)}
              >
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </div>
            <Title level={5} style={{ margin: 0, marginBottom: 4 }}>{pkg.name}</Title>
            {pkg.description && (
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                {pkg.description}
              </Text>
            )}
            <Space size={8}>
              <Tag color="blue">{pkg.dish_count}道菜</Tag>
              {pkg.base_price > 0 && <Tag color="green">¥{pkg.base_price}</Tag>}
            </Space>
          </Card>
        ))}
        {group.packages.length > 0 && (
          <Card
            hoverable
            style={{ width: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', borderStyle: 'dashed' }}
            styles={{ body: { textAlign: 'center', padding: 16 } }}
          >
            <Space direction="vertical" size={8}>
              <Button type="text" icon={<PlusOutlined />} onClick={() => handleNewEmptyPackage(group.id)}>
                手动新建
              </Button>
              <Button type="text" icon={<RobotOutlined />} onClick={() => { setAiGroupId(group.id); setAiModalOpen(true); }}>
                AI 生成
              </Button>
            </Space>
          </Card>
        )}
      </div>
    ),
  }));

  return (
    <div>
      {/* 顶栏参数 */}
      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '16px 24px' } }}>
        <Space size={24} wrap>
          <Space>
            <Text strong>客户名</Text>
            <Input
              placeholder="输入客户名"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              style={{ width: 140 }}
            />
          </Space>
          <Space>
            <Text strong>日期</Text>
            <DatePicker
              value={dayjs(date)}
              onChange={(d) => d && setDate(d.format('YYYY-MM-DD'))}
              allowClear={false}
            />
          </Space>
          <Space>
            <Text strong>人数</Text>
            <InputNumber
              min={1}
              max={200}
              value={partySize}
              onChange={(v) => setPartySize(v || 10)}
              style={{ width: 80 }}
            />
          </Space>
          <Space>
            <Text strong>桌数</Text>
            <InputNumber
              min={1}
              max={100}
              value={tableCount}
              onChange={(v) => setTableCount(v || 1)}
              style={{ width: 80 }}
            />
          </Space>
        </Space>
      </Card>

      {/* 套餐选择区 */}
      <Card
        title={
          <Space>
            <AppstoreOutlined />
            <span>选择套餐</span>
          </Space>
        }
        extra={
          <Button size="small" onClick={() => setNewGroupModalOpen(true)}>
            新建分组
          </Button>
        }
      >
        <Spin spinning={fetchingGroups || loading}>
          {groups.length === 0 && !fetchingGroups ? (
            <Empty description="还没有套餐分组">
              <Button type="primary" onClick={() => setNewGroupModalOpen(true)}>
                创建第一个分组
              </Button>
            </Empty>
          ) : (
            <Tabs items={tabItems} />
          )}
        </Spin>
      </Card>

      {/* 新建分组 Modal */}
      <Modal
        title="新建套餐分组"
        open={newGroupModalOpen}
        onOk={handleCreateGroup}
        onCancel={() => setNewGroupModalOpen(false)}
        okText="创建"
      >
        <Input
          placeholder="分组名称（如：散客、宴席、商务）"
          value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
          onPressEnter={handleCreateGroup}
        />
      </Modal>

      {/* AI 创建套餐 Modal */}
      <Modal
        title="AI 生成套餐"
        open={aiModalOpen}
        onOk={handleAICreate}
        onCancel={() => { setAiModalOpen(false); setAiDescription(''); }}
        okText="生成"
        confirmLoading={aiLoading}
      >
        <Input.TextArea
          rows={4}
          placeholder="描述你想要的套餐，如：10人商务宴请，以海鲜为主，4个凉菜6个热菜1个汤1个主食"
          value={aiDescription}
          onChange={(e) => setAiDescription(e.target.value)}
        />
      </Modal>

      {/* 套餐模板编辑 Drawer */}
      <Drawer
        title="编辑套餐模板"
        placement="right"
        width={720}
        open={editorOpen}
        onClose={() => {
          setEditorOpen(false);
          setEditingPackageId(null);
          fetchGroups();
        }}
        destroyOnClose
      >
        {editingPackageId && (
          <PackageTemplateEditor
            packageId={editingPackageId}
            user={user}
            onClose={() => {
              setEditorOpen(false);
              setEditingPackageId(null);
              fetchGroups();
            }}
          />
        )}
      </Drawer>
    </div>
  );
}
