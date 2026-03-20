import { useEffect, useRef, useState } from 'react';
import {
  Card, Input, InputNumber, DatePicker, Button, Space, Empty,
  message, Spin, Tag, Modal, Drawer, Typography, Popconfirm,
} from 'antd';
import {
  PlusOutlined, EditOutlined, RobotOutlined, AppstoreOutlined, DeleteOutlined,
  LeftOutlined, RightOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getPackageGroups, createMenuFromPackage, aiCreatePackage,
  createPackageGroup, updatePackageGroup, deletePackageGroup,
  createPackage, deletePackage,
} from '../api/menuApi';
import type { PackageGroup, PackageSummary, MenuData, User } from '../api/menuApi';
import PackageTemplateEditor from './PackageTemplateEditor';

const { Text, Title } = Typography;

const SCROLL_STEP_RATIO = 0.8;

interface Props {
  user: User;
  onMenuCreated: (menu: MenuData) => void;
  loading: boolean;
  setLoading: (v: boolean) => void;
}

interface TrackScrollState {
  canScrollLeft: boolean;
  canScrollRight: boolean;
}

const DEFAULT_SCROLL_STATE: TrackScrollState = {
  canScrollLeft: false,
  canScrollRight: false,
};

export default function PackageSelector({ user, onMenuCreated, loading, setLoading }: Props) {
  const [groups, setGroups] = useState<PackageGroup[]>([]);
  const [customerName, setCustomerName] = useState('');
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [partySize, setPartySize] = useState(10);
  const [tableCount, setTableCount] = useState(1);
  const [fetchingGroups, setFetchingGroups] = useState(false);

  const [editingPackageId, setEditingPackageId] = useState<number | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<PackageGroup | null>(null);
  const [groupName, setGroupName] = useState('');
  const [groupSubmitting, setGroupSubmitting] = useState(false);

  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiDescription, setAiDescription] = useState('');
  const [aiGroupId, setAiGroupId] = useState<number | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const trackRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const [trackScrollStates, setTrackScrollStates] = useState<Record<number, TrackScrollState>>({});

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

  useEffect(() => {
    fetchGroups();
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      groups.forEach((group) => syncTrackScrollState(group.id));
    });
    return () => window.cancelAnimationFrame(frame);
  }, [groups]);

  const syncTrackScrollState = (groupId: number) => {
    const track = trackRefs.current[groupId];
    if (!track) {
      return;
    }

    const maxScrollLeft = track.scrollWidth - track.clientWidth;
    const nextState = {
      canScrollLeft: track.scrollLeft > 4,
      canScrollRight: maxScrollLeft > 4 && track.scrollLeft < maxScrollLeft - 4,
    };

    setTrackScrollStates((prev) => {
      const current = prev[groupId];
      if (
        current
        && current.canScrollLeft === nextState.canScrollLeft
        && current.canScrollRight === nextState.canScrollRight
      ) {
        return prev;
      }
      return { ...prev, [groupId]: nextState };
    });
  };

  const scrollTrack = (groupId: number, direction: 'left' | 'right') => {
    const track = trackRefs.current[groupId];
    if (!track) return;

    const offset = track.clientWidth * SCROLL_STEP_RATIO * (direction === 'right' ? 1 : -1);
    track.scrollBy({ left: offset, behavior: 'smooth' });
    window.setTimeout(() => syncTrackScrollState(groupId), 280);
  };

  const openGroupModal = (group?: PackageGroup) => {
    setEditingGroup(group ?? null);
    setGroupName(group?.name ?? '');
    setGroupModalOpen(true);
  };

  const closeGroupModal = () => {
    setGroupModalOpen(false);
    setEditingGroup(null);
    setGroupName('');
  };

  const handleSubmitGroup = async () => {
    const nextName = groupName.trim();
    if (!nextName) return;

    setGroupSubmitting(true);
    try {
      if (editingGroup) {
        await updatePackageGroup(editingGroup.id, { name: nextName });
        message.success('分组名称已更新');
      } else {
        await createPackageGroup(nextName);
        message.success('分组已创建');
      }
      closeGroupModal();
      await fetchGroups();
    } catch (e: any) {
      message.error(e.message || '保存分组失败');
    } finally {
      setGroupSubmitting(false);
    }
  };

  const handleDeleteGroup = async (group: PackageGroup) => {
    if (group.packages.length > 0) {
      message.warning('分组下仍有套餐，请先清空后再删除');
      return;
    }

    try {
      await deletePackageGroup(group.id);
      message.success(`分组「${group.name}」已删除`);
      await fetchGroups();
    } catch (e: any) {
      message.error(e.message || '删除分组失败');
    }
  };

  const openAIModal = (groupId: number) => {
    setAiGroupId(groupId);
    setAiDescription('');
    setAiModalOpen(true);
  };

  const closeAIModal = () => {
    setAiModalOpen(false);
    setAiDescription('');
    setAiGroupId(null);
  };

  const handleSelectPackage = async (pkg: PackageSummary) => {
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
        package_id: pkg.id,
        pricing_mode: pkg.default_pricing_mode,
      });
      onMenuCreated(menu);
      message.success('菜单已创建');
    } catch (e: any) {
      message.error(e.message || '创建菜单失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAICreate = async () => {
    if (!aiDescription.trim() || !aiGroupId) return;

    setAiLoading(true);
    try {
      const result = await aiCreatePackage(aiDescription.trim(), aiGroupId);
      message.success(`AI 套餐「${result.name}」已创建`);
      closeAIModal();
      await fetchGroups();
    } catch (e: any) {
      message.error(e.message || 'AI 创建失败');
    } finally {
      setAiLoading(false);
    }
  };

  const handleNewEmptyPackage = async (groupId: number) => {
    const name = `新套餐 ${dayjs().format('MM-DD HH:mm')}`;
    try {
      const result = await createPackage({ group_id: groupId, name });
      message.success('空套餐已创建，请编辑');
      await fetchGroups();
      setEditingPackageId(result.id);
      setEditorOpen(true);
    } catch (e: any) {
      message.error(e.message || '创建套餐失败');
    }
  };

  const handleDeletePackage = async (packageId: number, packageName: string) => {
    try {
      await deletePackage(packageId);
      message.success(`套餐「${packageName}」已删除`);
      await fetchGroups();
    } catch (e: any) {
      message.error(e.message || '删除套餐失败');
    }
  };

  return (
    <div>
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

      <Card
        title={(
          <Space>
            <AppstoreOutlined />
            <span>选择套餐</span>
          </Space>
        )}
        extra={(
          <Button size="small" onClick={() => openGroupModal()}>
            新建分组
          </Button>
        )}
      >
        <Spin spinning={fetchingGroups || loading}>
          {groups.length === 0 && !fetchingGroups ? (
            <Empty description="还没有套餐分组">
              <Button type="primary" onClick={() => openGroupModal()}>
                创建第一个分组
              </Button>
            </Empty>
          ) : (
            <div className="package-selector-sections">
              {groups.map((group) => {
                const hasPackages = group.packages.length > 0;
                const scrollState = trackScrollStates[group.id] || DEFAULT_SCROLL_STATE;

                return (
                  <section key={group.id} className="package-section">
                    <div className="package-section-header">
                      <div className="package-section-heading">
                        <Space size={12} wrap>
                          <Title level={5} style={{ margin: 0 }}>{group.name}</Title>
                          <Tag color="blue">{group.packages.length} 套套餐</Tag>
                          {!hasPackages && <Tag color="green">空分组可删除</Tag>}
                          {hasPackages && (
                            <Text type="secondary" className="package-section-hint">
                              仅空分组可删
                            </Text>
                          )}
                        </Space>
                      </div>
                      <Space wrap>
                        <Button size="small" icon={<EditOutlined />} onClick={() => openGroupModal(group)}>
                          编辑
                        </Button>
                        {hasPackages ? (
                          <Button size="small" danger icon={<DeleteOutlined />} disabled>
                            删除
                          </Button>
                        ) : (
                          <Popconfirm
                            title={`确认删除分组「${group.name}」？`}
                            okText="删除"
                            cancelText="取消"
                            onConfirm={() => handleDeleteGroup(group)}
                          >
                            <Button size="small" danger icon={<DeleteOutlined />}>
                              删除
                            </Button>
                          </Popconfirm>
                        )}
                        <Button size="small" icon={<PlusOutlined />} onClick={() => handleNewEmptyPackage(group.id)}>
                          手动新建套餐
                        </Button>
                        <Button size="small" icon={<RobotOutlined />} onClick={() => openAIModal(group.id)}>
                          AI 生成套餐
                        </Button>
                      </Space>
                    </div>

                    <div className="package-track-shell">
                      <Button
                        shape="circle"
                        className="package-scroll-button"
                        icon={<LeftOutlined />}
                        disabled={!hasPackages || !scrollState.canScrollLeft}
                        onClick={() => scrollTrack(group.id, 'left')}
                      />

                      {hasPackages ? (
                        <div
                          ref={(node) => {
                            trackRefs.current[group.id] = node;
                          }}
                          className="package-track"
                          onScroll={() => syncTrackScrollState(group.id)}
                        >
                          {group.packages.map((pkg) => (
                            <Card
                              key={pkg.id}
                              hoverable
                              className="package-card"
                              styles={{ body: { padding: 16 } }}
                              onClick={() => handleSelectPackage(pkg)}
                            >
                              <div
                                className="package-card-actions"
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

                              <Title level={5} className="package-card-title">
                                {pkg.name}
                              </Title>

                              {pkg.description ? (
                                <Text type="secondary" className="package-card-description">
                                  {pkg.description}
                                </Text>
                              ) : (
                                <Text type="secondary" className="package-card-description package-card-description-muted">
                                  点击从模板创建菜单
                                </Text>
                              )}

                              <div className="package-card-tags">
                                <Tag color="blue">{pkg.dish_count}道菜</Tag>
                                {pkg.default_pricing_mode === 'fixed' && <Tag color="gold">固定价</Tag>}
                                {pkg.base_price > 0 && <Tag color="green">¥{pkg.base_price}</Tag>}
                              </div>
                            </Card>
                          ))}

                          <Card className="package-card package-card-action" styles={{ body: { padding: 16 } }}>
                            <Space direction="vertical" size={8}>
                              <Button type="text" icon={<PlusOutlined />} onClick={() => handleNewEmptyPackage(group.id)}>
                                手动新建
                              </Button>
                              <Button type="text" icon={<RobotOutlined />} onClick={() => openAIModal(group.id)}>
                                AI 生成
                              </Button>
                            </Space>
                          </Card>
                        </div>
                      ) : (
                        <div className="package-track-empty">
                          <Empty description="暂无套餐">
                            <Space>
                              <Button onClick={() => handleNewEmptyPackage(group.id)}>手动新建</Button>
                              <Button icon={<RobotOutlined />} onClick={() => openAIModal(group.id)}>
                                AI 生成
                              </Button>
                            </Space>
                          </Empty>
                        </div>
                      )}

                      <Button
                        shape="circle"
                        className="package-scroll-button"
                        icon={<RightOutlined />}
                        disabled={!hasPackages || !scrollState.canScrollRight}
                        onClick={() => scrollTrack(group.id, 'right')}
                      />
                    </div>
                  </section>
                );
              })}
            </div>
          )}
        </Spin>
      </Card>

      <Modal
        title={editingGroup ? '编辑套餐分组' : '新建套餐分组'}
        open={groupModalOpen}
        onOk={handleSubmitGroup}
        onCancel={closeGroupModal}
        okText={editingGroup ? '保存' : '创建'}
        confirmLoading={groupSubmitting}
      >
        <Input
          placeholder="分组名称（如：散客、宴席、商务）"
          value={groupName}
          onChange={(e) => setGroupName(e.target.value)}
          onPressEnter={handleSubmitGroup}
        />
      </Modal>

      <Modal
        title="AI 生成套餐"
        open={aiModalOpen}
        onOk={handleAICreate}
        onCancel={closeAIModal}
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
