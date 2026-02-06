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
  Space,
  Tag,
} from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import type { MenuRequest } from '../api/menuApi';

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
    <Card
      title="AI 智能配菜"
      style={{ maxWidth: 600, margin: '0 auto' }}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ party_size: 8, budget: 3000, target_margin: 55 }}
      >
        <Space.Compact style={{ width: '100%' }}>
          <Form.Item
            label="客户名称"
            name="customer_name"
            style={{ flex: 1, marginRight: 12 }}
          >
            <Input placeholder="如：张总" />
          </Form.Item>
          <Form.Item label="日期" name="date" style={{ flex: 1 }}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Space.Compact>

        <Space style={{ width: '100%' }} size="large">
          <Form.Item
            label="人数"
            name="party_size"
            rules={[{ required: true, message: '请输入人数' }]}
          >
            <InputNumber min={2} max={30} addonAfter="人" />
          </Form.Item>
          <Form.Item
            label="预算"
            name="budget"
            rules={[{ required: true, message: '请输入预算' }]}
          >
            <InputNumber min={500} max={50000} step={100} addonAfter="元" />
          </Form.Item>
        </Space>

        <Form.Item label="目标毛利率" name="target_margin">
          <Slider min={30} max={80} marks={{ 30: '30%', 55: '55%', 80: '80%' }} />
        </Form.Item>

        <Form.Item label="场合" name="occasion">
          <Select placeholder="选择用餐场合">
            {occasions.map((o) => (
              <Select.Option key={o} value={o}>
                {o}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item label="偏好（可多选）">
          <div style={{ marginBottom: 8 }}>
            {preferenceTags.map((tag) => (
              <Tag.CheckableTag
                key={tag}
                checked={selectedTags.includes(tag)}
                onChange={() => toggleTag(tag)}
                style={{ marginBottom: 4 }}
              >
                {tag}
              </Tag.CheckableTag>
            ))}
          </div>
          <Form.Item name="extra_pref" noStyle>
            <Input placeholder="其他要求（选填）" />
          </Form.Item>
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            icon={<ThunderboltOutlined />}
            size="large"
            block
          >
            {loading ? 'AI 正在配菜...' : '开始智能配菜'}
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
