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
  Divider,
  message,
} from 'antd';
import {
  DownloadOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { MenuData, MenuItemData } from '../api/menuApi';
import { downloadExcel } from '../api/menuApi';

const { Title, Text } = Typography;

const CATEGORY_ORDER = ['凉菜', '热菜', '汤羹', '主食', '甜品', '点心'];
const CATEGORY_COLORS: Record<string, string> = {
  凉菜: 'blue',
  热菜: 'red',
  汤羹: 'orange',
  主食: 'green',
  甜品: 'pink',
  点心: 'purple',
};

interface Props {
  menu: MenuData;
  onRegenerate: () => void;
  loading: boolean;
}

export default function MenuPreview({ menu, onRegenerate, loading }: Props) {
  const [downloading, setDownloading] = useState(false);

  const budgetPercent = Math.round((menu.total_price / menu.budget) * 100);
  const marginOk = Math.abs(menu.margin_rate - menu.target_margin) <= 5;

  // 按类别分组并排序
  const sortedItems = [...menu.items].sort(
    (a, b) =>
      CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category)
  );

  const columns = [
    {
      title: '菜名',
      dataIndex: 'dish_name',
      key: 'dish_name',
      render: (name: string, record: MenuItemData) => (
        <Space>
          <Tag color={CATEGORY_COLORS[record.category] || 'default'}>
            {record.category}
          </Tag>
          {name}
          {record.price_text.includes('时价') && (
            <Tag color="warning">时价</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '单价',
      dataIndex: 'price_text',
      key: 'price_text',
      align: 'center' as const,
      width: 120,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'center' as const,
      width: 70,
    },
    {
      title: '小计',
      dataIndex: 'subtotal',
      key: 'subtotal',
      align: 'right' as const,
      width: 90,
      render: (v: number) => `¥${v.toFixed(0)}`,
    },
    {
      title: '成本',
      dataIndex: 'cost_total',
      key: 'cost_total',
      align: 'right' as const,
      width: 80,
      render: (v: number) => (
        <Text type="secondary">¥{v.toFixed(0)}</Text>
      ),
    },
    {
      title: '毛利率',
      key: 'item_margin',
      align: 'center' as const,
      width: 80,
      render: (_: unknown, record: MenuItemData) => {
        const margin =
          record.price > 0
            ? ((record.price - record.cost) / record.price) * 100
            : 0;
        return (
          <Text type={margin >= 50 ? 'success' : 'warning'}>
            {margin.toFixed(0)}%
          </Text>
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
    <Card style={{ maxWidth: 900, margin: '0 auto' }}>
      <Title level={4} style={{ textAlign: 'center', marginBottom: 4 }}>
        旺阁渔村 · 推荐菜单
      </Title>
      <Text
        type="secondary"
        style={{ display: 'block', textAlign: 'center', marginBottom: 16 }}
      >
        {menu.customer_name || '贵宾'} | {menu.party_size}人 | {menu.occasion || '聚餐'}
        {menu.date ? ` | ${menu.date}` : ''}
      </Text>

      {/* 汇总指标 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="预算使用"
              value={menu.total_price}
              suffix={`/ ${menu.budget}`}
              prefix="¥"
              valueStyle={{
                fontSize: 18,
                color: budgetPercent > 100 ? '#cf1322' : '#3f8600',
              }}
            />
            <Progress
              percent={Math.min(budgetPercent, 100)}
              status={budgetPercent > 105 ? 'exception' : 'active'}
              size="small"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="整单毛利率"
              value={menu.margin_rate}
              suffix="%"
              prefix={marginOk ? <CheckCircleOutlined /> : <WarningOutlined />}
              valueStyle={{
                fontSize: 18,
                color: marginOk ? '#3f8600' : '#faad14',
              }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              目标: {menu.target_margin}%
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="总成本"
              value={menu.total_cost}
              prefix="¥"
              valueStyle={{ fontSize: 18 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              利润: ¥{(menu.total_price - menu.total_cost).toFixed(0)}
            </Text>
          </Card>
        </Col>
      </Row>

      {/* AI 推荐理由 */}
      {menu.reasoning && (
        <Collapse
          ghost
          items={[
            {
              key: '1',
              label: 'AI 配菜思路',
              children: <Text>{menu.reasoning}</Text>,
            },
          ]}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 菜品列表 */}
      <Table
        dataSource={sortedItems}
        columns={columns}
        rowKey="dish_id"
        pagination={false}
        size="small"
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={3}>
              <Text strong>合计 ({menu.items.length} 道菜)</Text>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={3} align="right">
              <Text strong>¥{menu.total_price.toFixed(0)}</Text>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={4} align="right">
              <Text type="secondary">¥{menu.total_cost.toFixed(0)}</Text>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={5} align="center">
              <Text strong>{menu.margin_rate}%</Text>
            </Table.Summary.Cell>
          </Table.Summary.Row>
        )}
      />

      <Divider />

      {/* 操作按钮 */}
      <Space style={{ width: '100%', justifyContent: 'center' }}>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          size="large"
          onClick={handleDownload}
          loading={downloading}
        >
          下载 Excel
        </Button>
        <Button
          icon={<ReloadOutlined />}
          size="large"
          onClick={onRegenerate}
          loading={loading}
        >
          重新生成
        </Button>
      </Space>
    </Card>
  );
}
