
import { useState, useEffect } from 'react';
import { Table, Button, Switch, Modal, Form, InputNumber, Input, Select, message, Tag, Space } from 'antd';
import { getDishes, updateDish } from '../api/menuApi';
import type { Dish, User } from '../api/menuApi';

interface DishManagerProps {
    user: User;
}

const DishManager = ({ user }: DishManagerProps) => {
    const [dishes, setDishes] = useState<Dish[]>([]);
    const [loading, setLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingDish, setEditingDish] = useState<Dish | null>(null);
    const [form] = Form.useForm();

    const isAdmin = user.role === 'admin';

    const fetchDishes = async () => {
        setLoading(true);
        try {
            const data = await getDishes();
            setDishes(data);
        } catch (e: any) {
            message.error(e.message || "加载失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDishes();
    }, []);

    const handleToggleActive = async (dish: Dish, checked: boolean) => {
        try {
            const updated = await updateDish(dish.id, { is_active: checked });
            message.success(`${dish.name} 已${checked ? '上架' : '下架'}`);
            setDishes((prev) => prev.map((d) => (d.id === dish.id ? { ...d, ...updated } : d)));
        } catch (e: any) {
            message.error(e.message || "操作失败");
            fetchDishes();
        }
    };

    const handleToggleTag = async (
        dish: Dish,
        field: 'is_signature' | 'is_must_order',
        checked: boolean
    ) => {
        try {
            const updated = await updateDish(dish.id, { [field]: checked });
            message.success(`${dish.name} 已${checked ? '设置' : '取消'}${field === 'is_signature' ? '招牌菜' : '必点菜'}`);
            setDishes((prev) => prev.map((d) => (d.id === dish.id ? { ...d, ...updated } : d)));
        } catch (e: any) {
            message.error(e.message || "操作失败");
            fetchDishes();
        }
    };

    const openEditModal = (dish: Dish) => {
        setEditingDish(dish);
        form.setFieldsValue({
            price: dish.price,
            cost: dish.cost,
            min_price: dish.min_price,
            price_text: dish.price_text,
            serving_unit: dish.serving_unit || "",
            serving_split: dish.serving_split || 0,
            is_signature: !!dish.is_signature,
            is_must_order: !!dish.is_must_order,
        });
        setIsModalOpen(true);
    };

    const handleUpdate = async () => {
        try {
            const values = await form.validateFields();
            if (!editingDish) return;

            await updateDish(editingDish.id, values);
            message.success("更新成功");
            setIsModalOpen(false);
            setEditingDish(null);
            fetchDishes();
        } catch (e: any) {
            message.error(e.message || "更新失败");
        }
    };

    const columns = [
        { title: 'ID', dataIndex: 'id', width: 60, align: 'center' as const },
        {
            title: '菜名',
            dataIndex: 'name',
            width: 150,
            render: (text: string, record: Dish) => (
                <Space>
                    {text}
                    {!record.is_active && <Tag color="default">已下架</Tag>}
                    {record.is_signature && <Tag color="gold">招牌</Tag>}
                    {record.is_must_order && <Tag color="volcano">必点</Tag>}
                </Space>
            )
        },
        {
            title: '分类',
            dataIndex: 'category',
            width: 80,
            filters: [
                { text: '凉菜', value: '凉菜' },
                { text: '热菜', value: '热菜' },
                { text: '主食', value: '主食' },
                { text: '汤羹', value: '汤羹' },
                { text: '甜品', value: '甜品' },
                { text: '点心', value: '点心' },
            ],
            onFilter: (value: any, record: Dish) => record.category === value,
        },
        { title: '售价描述', dataIndex: 'price_text', width: 120 },
        {
            title: '售价(¥)',
            dataIndex: 'price',
            width: 100,
            render: (price: number) => `¥${price}`
        },
        {
            title: '成本(¥)',
            dataIndex: 'cost',
            width: 100,
            render: (cost: number) => (
                isAdmin ? <span style={{ color: '#faad14', fontWeight: 'bold' }}>¥{cost}</span> : '***'
            )
        },
        {
            title: '底价(¥)',
            dataIndex: 'min_price',
            width: 100,
            render: (min_price: number) => (
                isAdmin ? <span style={{ color: '#fa8c16' }}>¥{min_price}</span> : '***'
            )
        },
        {
            title: '上菜单位',
            dataIndex: 'serving_unit',
            width: 90,
            render: (unit?: string) => unit || '-',
        },
        {
            title: '一开几',
            width: 90,
            render: (_: any, record: Dish) => {
                if (!record.serving_split || record.serving_split <= 0) {
                    return '-';
                }
                return <Tag color="cyan">一开{record.serving_split}</Tag>;
            },
        },
        {
            title: '招牌菜',
            width: 90,
            render: (_: any, record: Dish) => (
                <Switch
                    checked={!!record.is_signature}
                    onChange={(checked) => handleToggleTag(record, 'is_signature', checked)}
                    disabled={!isAdmin}
                />
            ),
        },
        {
            title: '必点菜',
            width: 90,
            render: (_: any, record: Dish) => (
                <Switch
                    checked={!!record.is_must_order}
                    onChange={(checked) => handleToggleTag(record, 'is_must_order', checked)}
                    disabled={!isAdmin}
                />
            ),
        },
        {
            title: '毛利率',
            width: 100,
            render: (_: any, record: Dish) => {
                if (!isAdmin) return '***';
                const margin = ((record.price - record.cost) / record.price * 100).toFixed(1);
                return `${margin}%`;
            }
        },
        {
            title: '状态 / 操作',
            width: 150,
            render: (_: any, record: Dish) => (
                <Space>
                    <Switch
                        checked={record.is_active}
                        onChange={(checked) => handleToggleActive(record, checked)}
                        checkedChildren="上架"
                        unCheckedChildren="下架"
                    />
                    {isAdmin && <Button size="small" type="link" onClick={() => openEditModal(record)}>编辑</Button>}
                </Space>
            )
        }
    ];

    return (
        <div style={{ padding: 24, background: '#fff', borderRadius: 8 }}>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>菜品数据管理 ({dishes.length})</h2>
                <Space>
                    <Button onClick={fetchDishes}>刷新列表</Button>
                </Space>
            </div>

            <Table
                dataSource={dishes}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={{ pageSize: 50, showSizeChanger: true }}
                size="small"
                scroll={{ y: 600 }}
            />

            <Modal
                title={editingDish ? `编辑: ${editingDish.name}` : "编辑菜品"}
                open={isModalOpen}
                onOk={handleUpdate}
                onCancel={() => setIsModalOpen(false)}
                okText="保存"
                cancelText="取消"
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="price" label="售价 (¥)" rules={[{ required: true }]}>
                        <InputNumber style={{ width: '100%' }} precision={2} />
                    </Form.Item>
                    <Form.Item name="cost" label="成本 (¥)" rules={[{ required: true }]}>
                        <InputNumber style={{ width: '100%' }} precision={2} />
                    </Form.Item>
                    <Form.Item name="min_price" label="底价 (¥) — 宴会模式定价下限">
                        <InputNumber style={{ width: '100%' }} precision={2} min={0} />
                    </Form.Item>
                    <Form.Item name="price_text" label="价格描述 (如: 98元/例)">
                        <Input />
                    </Form.Item>
                    <Form.Item name="serving_unit" label="上菜单位 (例/只/件/份)">
                        <Input placeholder="如：只" maxLength={8} />
                    </Form.Item>
                    <Form.Item name="serving_split" label="一开几">
                        <Select
                            options={[
                                { value: 0, label: '不适用/不确定' },
                                { value: 2, label: '一开二' },
                                { value: 4, label: '一开四' },
                            ]}
                        />
                    </Form.Item>
                    <Space size={24}>
                        <Form.Item name="is_signature" label="招牌菜" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                        <Form.Item name="is_must_order" label="必点菜" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                    </Space>
                </Form>
            </Modal>
        </div>
    );
};

export default DishManager;
