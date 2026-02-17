
import { useState, useEffect } from 'react';
import { ConfigProvider, Input, Button, Card, Typography, message, theme, Layout, Menu as AntMenu, Space, Tag } from 'antd';
import { LockOutlined, UserOutlined, UnorderedListOutlined, FormOutlined, LogoutOutlined } from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import { login, generateMenu, getMe } from './api/menuApi';
import type { MenuRequest, MenuData, User } from './api/menuApi';
import OrderForm from './components/OrderForm';
import MenuPreview from './components/MenuPreview';
import DishManager from './components/DishManager';
import './App.css';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [menuData, setMenuData] = useState<MenuData | null>(null);
  const [view, setView] = useState<'menu' | 'dishes'>('menu'); // 'menu' | 'dishes'

  useEffect(() => {
    // Check if already logged in
    getMe()
      .then((u) => {
        setUser(u);
        setIsLoggedIn(true);
      })
      .catch(() => {
        // Token invalid or expired
        localStorage.removeItem('wg_token');
      });
  }, []);

  const handleLogin = async () => {
    if (!username || !password) {
      message.error('请输入用户名和密码');
      return;
    }
    setLoading(true);
    try {
      const u = await login(username, password);
      setUser(u);
      setIsLoggedIn(true);
      message.success(`欢迎回来，${u.full_name || u.username}`);
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('wg_token');
    setIsLoggedIn(false);
    setUser(null);
    setMenuData(null);
    setView('menu');
    setUsername('');
    setPassword('');
  };

  const handleSubmit = async (req: MenuRequest) => {
    setLoading(true);
    setMenuData(null);
    try {
      const data = await generateMenu(req);
      setMenuData(data);
      message.success('菜单生成成功！');
    } catch (error: any) {
      message.error(error.message || '生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = () => {
    setMenuData(null);
  };

  // Login Screen
  if (!isLoggedIn) {
    return (
      <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
        <div style={{
          height: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #1890ff 0%, #8b5cf6 100%)'
        }}>
          <Card style={{ width: 400, textAlign: 'center', borderRadius: 16, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
            <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>旺阁渔村</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>AI 智能点菜系统</Text>

            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Input
                prefix={<UserOutlined />}
                placeholder="用户名 (admin / chef)"
                size="large"
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
                size="large"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onPressEnter={handleLogin}
              />
              <Button type="primary" size="large" block onClick={handleLogin} loading={loading}>
                登 录
              </Button>
            </Space>
          </Card>
        </div>
      </ConfigProvider>
    );
  }

  // Main App
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#8b5cf6',
          borderRadius: 8,
        },
      }}
    >
      <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
          position: 'sticky', top: 0, zIndex: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Title level={4} style={{ margin: 0, color: '#8b5cf6' }}>旺阁渔村 AI</Title>
            <AntMenu
              mode="horizontal"
              selectedKeys={[view]}
              onClick={(e) => setView(e.key as any)}
              items={[
                { key: 'menu', icon: <FormOutlined />, label: '点菜生成' },
                { key: 'dishes', icon: <UnorderedListOutlined />, label: '菜品管理' },
              ]}
              style={{ borderBottom: 'none', width: 300 }}
            />
          </div>
          <Space>
            <Tag color={user?.role === 'admin' ? 'red' : 'blue'}>
              {user?.full_name || user?.username} ({user?.role === 'admin' ? '管理员' : '员工'})
            </Tag>
            <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>退出</Button>
          </Space>
        </Header>

        <Content style={{ padding: '24px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
          {view === 'menu' ? (
            !menuData ? (
              <OrderForm onSubmit={handleSubmit} loading={loading} />
            ) : (
              <MenuPreview
                menu={menuData}
                onRegenerate={handleRegenerate}
                onMenuUpdated={(nextMenu) => setMenuData(nextMenu)}
                loading={loading}
              />
            )
          ) : (
            <DishManager user={user!} />
          )}
        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
