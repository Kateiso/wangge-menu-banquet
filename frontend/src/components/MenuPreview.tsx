import { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Button,
  Typography,
  Space,
  Collapse,
  Statistic,
  Row,
  Col,
  message,
} from 'antd';
import {
  DownloadOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { MenuData, MenuItemData } from '../api/menuApi';
import { downloadExcel } from '../api/menuApi';
import MenuAdjustChat from './MenuAdjustChat';

const { Title, Text } = Typography;

const CATEGORY_ORDER = ['凉菜', '热菜', '汤羹', '主食', '甜品', '点心'];
const CATEGORY_COLORS: Record<string, string> = {
  凉菜: '#818cf8',
  热菜: '#f472b6',
  汤羹: '#fb923c',
  主食: '#34d399',
  甜品: '#f9a8d4',
  点心: '#a78bfa',
};

interface Props {
  menu: MenuData;
  onRegenerate: () => void;
  onMenuUpdated: (menu: MenuData) => void;
  loading: boolean;
}

export default function MenuPreview({ menu, onRegenerate, onMenuUpdated, loading }: Props) {
  const [downloading, setDownloading] = useState(false);

  const isBanquet = menu.mode === 'banquet';
  const budgetPercent = Math.round((menu.total_price / menu.budget) * 100);
  const marginOk = Math.abs(menu.margin_rate - menu.target_margin) <= 5;

  const sortedItems = [...menu.items].sort(
    (a, b) =>
      CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category)
  );

  const columns = [
    {
      title: '菜品',
      dataIndex: 'dish_name',
      key: 'dish_name',
      render: (name: string, record: MenuItemData) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Tag
            className="cat-tag"
            color={CATEGORY_COLORS[record.category] || '#d1d5db'}
          >
            {record.category}
          </Tag>
          <span style={{ fontWeight: 500, color: '#1f2937' }}>{name}</span>
          {record.price_text.includes('时价') && (
            <Tag
              style={{
                background: 'rgba(251, 146, 60, 0.1)',
                color: '#f97316',
                border: 'none',
                borderRadius: 8,
                fontSize: 11,
              }}
            >
              时价
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: '单价',
      dataIndex: 'price_text',
      key: 'price_text',
      align: 'center' as const,
      width: 120,
      render: (v: string) => <span style={{ color: '#6b7280' }}>{v}</span>,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'center' as const,
      width: 70,
      render: (v: number) => (
        <span
          style={{
            background: 'rgba(139, 92, 246, 0.08)',
            padding: '2px 10px',
            borderRadius: 8,
            fontWeight: 600,
            color: '#7c3aed',
            fontSize: 13,
          }}
        >
          {v}
        </span>
      ),
    },
    {
      title: '小计',
      dataIndex: 'subtotal',
      key: 'subtotal',
      align: 'right' as const,
      width: 90,
      render: (v: number) => (
        <span style={{ fontWeight: 600, color: '#1f2937' }}>
          ¥{v.toFixed(0)}
        </span>
      ),
    },
    {
      title: '成本',
      dataIndex: 'cost_total',
      key: 'cost_total',
      align: 'right' as const,
      width: 80,
      render: (v: number) => (
        <span style={{ color: '#9ca3af', fontSize: 13 }}>¥{v.toFixed(0)}</span>
      ),
    },
    {
      title: '毛利',
      key: 'item_margin',
      align: 'center' as const,
      width: 80,
      render: (_: unknown, record: MenuItemData) => {
        const margin =
          record.price > 0
            ? ((record.price - record.cost) / record.price) * 100
            : 0;
        const color = margin >= 60 ? '#10b981' : margin >= 50 ? '#f59e0b' : '#ef4444';
        return (
          <span
            style={{
              color,
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            {margin.toFixed(0)}%
          </span>
        );
      },
    },
  ];

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadExcel(menu.id);
      message.success('Excel 下载成功');
    } catch {
      message.error('下载失败，请重试');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Row gutter={[20, 20]}>
      {/* 左侧：菜单 */}
      <Col xs={24} lg={16}>
        <Card className="glass-card" styles={{ body: { padding: '24px' } }}>
          {/* 标题 */}
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <Title level={4} style={{ marginBottom: 4, color: '#1f2937', fontWeight: 700 }}>
              {isBanquet ? '宴会菜单' : '推荐菜单'}
            </Title>
            <Space
              split={<span style={{ color: '#d1d5db' }}>·</span>}
              size={8}
            >
              <Text style={{ color: '#6b7280', fontSize: 13 }}>
                {menu.customer_name || '贵宾'}
              </Text>
              <Text style={{ color: '#6b7280', fontSize: 13 }}>
                {menu.party_size}人
              </Text>
              <Text style={{ color: '#6b7280', fontSize: 13 }}>
                {menu.occasion || '聚餐'}
              </Text>
              {menu.date && (
                <Text style={{ color: '#6b7280', fontSize: 13 }}>
                  {menu.date}
                </Text>
              )}
            </Space>
          </div>

          {/* 统计卡片 */}
          <Row gutter={12} style={{ marginBottom: 20 }}>
            <Col span={8}>
              <Card size="small" className="stat-card stat-card-budget">
                {isBanquet ? (
                  <>
                    <Statistic
                      title="宴会总价"
                      value={menu.total_price}
                      prefix="¥"
                      valueStyle={{ fontSize: 18 }}
                    />
                    <div style={{ marginTop: 4 }}>
                      <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>
                        按预算定价
                      </Text>
                    </div>
                  </>
                ) : (
                  <>
                    <Statistic
                      title="预算使用"
                      value={menu.total_price}
                      suffix={`/ ${menu.budget}`}
                      prefix="¥"
                      valueStyle={{ fontSize: 18 }}
                    />
                    <Progress
                      percent={Math.min(budgetPercent, 100)}
                      showInfo={false}
                      size="small"
                      style={{ marginTop: 4 }}
                    />
                  </>
                )}
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" className="stat-card stat-card-margin">
                <Statistic
                  title="整单毛利"
                  value={menu.margin_rate}
                  suffix="%"
                  valueStyle={{ fontSize: 18 }}
                />
                <div style={{ marginTop: 4 }}>
                  <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>
                    {marginOk ? '达标' : '偏差'} · 目标 {menu.target_margin}%
                  </Text>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" className="stat-card stat-card-cost">
                <Statistic
                  title="成本 / 利润"
                  value={menu.total_cost}
                  prefix="¥"
                  valueStyle={{ fontSize: 18 }}
                />
                <div style={{ marginTop: 4 }}>
                  <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>
                    利润 ¥{(menu.total_price - menu.total_cost).toFixed(0)}
                  </Text>
                </div>
              </Card>
            </Col>
          </Row>

          {/* AI 推荐理由 */}
          {menu.reasoning && (
            <Collapse
              ghost
              className="reasoning-collapse"
              items={[
                {
                  key: '1',
                  label: (
                    <span style={{ fontSize: 13 }}>
                      AI 配菜思路
                    </span>
                  ),
                  children: (
                    <Text style={{ color: '#6b7280', lineHeight: 1.8, fontSize: 13 }}>
                      {menu.reasoning}
                    </Text>
                  ),
                },
              ]}
              style={{ marginBottom: 16 }}
            />
          )}

          {/* 菜品表格 */}
          <div className="menu-table">
            <Table
              dataSource={sortedItems}
              columns={columns}
              rowKey="dish_id"
              pagination={false}
              size="small"
              summary={() => (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={3}>
                    <Text strong style={{ color: '#4b5563' }}>
                      合计 {menu.items.length} 道菜
                    </Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">
                    <Text strong style={{ color: '#1f2937', fontSize: 15 }}>
                      ¥{menu.total_price.toFixed(0)}
                    </Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4} align="right">
                    <Text style={{ color: '#9ca3af' }}>
                      ¥{menu.total_cost.toFixed(0)}
                    </Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="center">
                    <Text strong style={{ color: '#8b5cf6' }}>
                      {menu.margin_rate}%
                    </Text>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              )}
            />
          </div>

          {/* 宴会模式说明 */}
          {isBanquet && (
            <div style={{
              marginTop: 12,
              padding: '8px 12px',
              background: 'rgba(139, 92, 246, 0.06)',
              borderRadius: 8,
              fontSize: 13,
              color: '#6b7280',
            }}>
              宴会模式：单价由系统按预算自动分配，非原始菜牌价
            </div>
          )}

          {/* 操作按钮 */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: 12,
              marginTop: 24,
              paddingTop: 20,
              borderTop: '1px solid rgba(139, 92, 246, 0.08)',
            }}
          >
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              size="large"
              onClick={handleDownload}
              loading={downloading}
              className="btn-gradient"
              style={{ minWidth: 140 }}
            >
              下载 Excel
            </Button>
            <Button
              icon={<ReloadOutlined />}
              size="large"
              onClick={onRegenerate}
              loading={loading}
              className="btn-secondary"
              style={{ minWidth: 120 }}
            >
              重新生成
            </Button>
          </div>
        </Card>
      </Col>

      {/* 右侧：对话调整 */}
      <Col xs={24} lg={8}>
        <MenuAdjustChat menuId={menu.id} onMenuUpdated={onMenuUpdated} />
      </Col>
    </Row>
  );
}
