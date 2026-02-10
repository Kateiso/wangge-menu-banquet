import { useState } from 'react';
import {
  Form,
  InputNumber,
  Slider,
  Select,
  Input,
  Button,
  DatePicker,
  Card,
  Typography,
  Row,
  Col,
} from 'antd';
import type { MenuRequest } from '../api/menuApi';

const { Title, Text } = Typography;

const occasions = [
  '商务宴请',
  '家庭聚餐',
  '朋友聚会',
  '生日宴',
  '庆功宴',
  '普通聚餐',
];

const preferenceTags = [
  '海鲜为主',
  '不吃辣',
  '偏辣',
  '要有鸡',
  '要有鱼',
  '要招牌菜',
  '清淡为主',
  '有小朋友',
  '养生滋补',
  '高端大气',
  '实惠为主',
];

interface Props {
  onSubmit: (req: MenuRequest) => void;
  loading: boolean;
}

export default function OrderForm({ onSubmit, loading }: Props) {
  const [form] = Form.useForm();
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const handleFinish = (values: Record<string, unknown>) => {
    const prefs = [...selectedTags];
    if (values.extra_pref) prefs.push(values.extra_pref as string);

    const req: MenuRequest = {
      customer_name: (values.customer_name as string) || '',
      party_size: values.party_size as number,
      budget: values.budget as number,
      target_margin: values.target_margin as number,
      occasion: (values.occasion as string) || '普通聚餐',
      preferences: prefs.join('，'),
      date: values.date ? (values.date as { format: (f: string) => string }).format('YYYY-MM-DD') : '',
    };
    onSubmit(req);
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto' }}>
      {/* 标题区域 */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4, color: '#1f2937', fontWeight: 700 }}>
          智能配菜
        </Title>
        <Text style={{ color: '#9ca3af', fontSize: 14 }}>
          填写需求，AI 为您推荐最佳菜品方案
        </Text>
      </div>

      <Card className="glass-card modern-form" style={{ padding: '8px 4px' }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          initialValues={{ party_size: 8, budget: 3000, target_margin: 55 }}
          size="large"
        >
          {/* 客户信息 */}
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item label="客户名称" name="customer_name">
                <Input placeholder="如：张总" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="用餐日期" name="date">
                <DatePicker style={{ width: '100%' }} placeholder="选择日期" />
              </Form.Item>
            </Col>
          </Row>

          {/* 人数 & 预算 */}
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item
                label="用餐人数"
                name="party_size"
                rules={[{ required: true, message: '请输入人数' }]}
              >
                <InputNumber
                  min={2}
                  max={30}
                  addonAfter="人"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="预算金额"
                name="budget"
                rules={[{ required: true, message: '请输入预算' }]}
              >
                <InputNumber
                  min={500}
                  max={50000}
                  step={100}
                  addonAfter="元"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 毛利率 */}
          <Form.Item
            label={
              <span>
                目标毛利率
                <span style={{ color: '#9ca3af', fontWeight: 400, marginLeft: 8, fontSize: 13 }}>
                  滑动调整
                </span>
              </span>
            }
            name="target_margin"
          >
            <Slider
              min={30}
              max={80}
              marks={{
                30: { label: <span style={{ fontSize: 12 }}>30%</span> },
                55: { label: <span style={{ fontSize: 12, color: '#8b5cf6', fontWeight: 600 }}>55%</span> },
                80: { label: <span style={{ fontSize: 12 }}>80%</span> },
              }}
            />
          </Form.Item>

          {/* 场合 */}
          <Form.Item label="用餐场合" name="occasion">
            <Select placeholder="选择用餐场合">
              {occasions.map((o) => (
                <Select.Option key={o} value={o}>
                  {o}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {/* 偏好标签 */}
          <Form.Item
            label={
              <span>
                口味偏好
                <span style={{ color: '#9ca3af', fontWeight: 400, marginLeft: 8, fontSize: 13 }}>
                  可多选
                </span>
              </span>
            }
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
              {preferenceTags.map((tag) => {
                const active = selectedTags.includes(tag);
                return (
                  <span
                    key={tag}
                    className={`pref-tag ${active ? 'pref-tag-active' : ''}`}
                    onClick={() => toggleTag(tag)}
                    role="checkbox"
                    aria-checked={active}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleTag(tag);
                      }
                    }}
                  >
                    {tag}
                  </span>
                );
              })}
            </div>
            <Form.Item name="extra_pref" noStyle>
              <Input placeholder="其他要求（选填）" />
            </Form.Item>
          </Form.Item>

          {/* 提交 */}
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              size="large"
              block
              className="btn-gradient"
              style={{ height: 52, fontSize: 16 }}
            >
              {loading ? 'AI 正在配菜...' : '开始智能配菜'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
