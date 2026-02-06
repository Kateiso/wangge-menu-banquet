import { useState, useEffect, useRef } from 'react';
import { ConfigProvider, Layout, Input, Button, Card, Typography, message, Spin } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import OrderForm from './components/OrderForm';
import MenuPreview from './components/MenuPreview';
import { login, generateMenu } from './api/menuApi';
import type { MenuRequest, MenuData } from './api/menuApi';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('wg_token'));
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [menu, setMenu] = useState<MenuData | null>(null);
  const lastRequest = useRef<MenuRequest | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleLogin = async () => {
    setLoginLoading(true);
    const ok = await login(password);
    setLoginLoading(false);
    if (ok) {
      setAuthed(true);
      message.success('登录成功');
    } else {
      message.error('密码错误');
    }
  };

  const handleSubmit = async (req: MenuRequest) => {
    lastRequest.current = req;
    setLoading(true);
    setMenu(null);

    // 30s 超时
    const timeout = new Promise<never>((_, reject) => {
      timerRef.current = setTimeout(() => reject(new Error('timeout')), 30000);
    });

    try {
      const data = await Promise.race([generateMenu(req), timeout]);
      setMenu(data);
    } catch (err) {
      if (err instanceof Error && err.message === 'timeout') {
        message.warning('AI 配菜超时，请重试');
      } else {
        message.error(err instanceof Error ? err.message : '生成失败');
      }
    } finally {
      setLoading(false);
      if (timerRef.current) clearTimeout(timerRef.current);
    }
  };

  const handleRegenerate = () => {
    if (lastRequest.current) {
      handleSubmit(lastRequest.current);
    }
  };

  // 登录页
  if (!authed) {
    return (
      <ConfigProvider locale={zhCN}>
        <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
          <Content
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <Card style={{ width: 360, textAlign: 'center' }}>
              <Title level={3} style={{ marginBottom: 4 }}>
                旺阁渔村
              </Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
                AI 智能点菜系统
              </Text>
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onPressEnter={handleLogin}
                style={{ marginBottom: 16 }}
                size="large"
              />
              <Button
                type="primary"
                block
                size="large"
                loading={loginLoading}
                onClick={handleLogin}
              >
                进入系统
              </Button>
            </Card>
          </Content>
        </Layout>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={zhCN}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header
          style={{
            background: '#001529',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
          }}
        >
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            旺阁渔村 · AI 智能点菜
          </Title>
          <Button
            type="link"
            style={{ color: '#aaa' }}
            onClick={() => {
              localStorage.removeItem('wg_token');
              setAuthed(false);
              setMenu(null);
            }}
          >
            退出
          </Button>
        </Header>
        <Content style={{ padding: '24px', maxWidth: 1000, margin: '0 auto', width: '100%' }}>
          {!menu && !loading && <OrderForm onSubmit={handleSubmit} loading={loading} />}

          {loading && (
            <Card style={{ textAlign: 'center', maxWidth: 600, margin: '0 auto' }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>
                <Title level={4}>AI 正在配菜...</Title>
                <Text type="secondary">
                  根据您的需求智能搭配菜品，请稍候
                </Text>
              </div>
            </Card>
          )}

          {menu && (
            <>
              <MenuPreview
                menu={menu}
                onRegenerate={handleRegenerate}
                loading={loading}
              />
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Button
                  type="link"
                  onClick={() => {
                    setMenu(null);
                    lastRequest.current = null;
                  }}
                >
                  返回重新下单
                </Button>
              </div>
            </>
          )}
        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
