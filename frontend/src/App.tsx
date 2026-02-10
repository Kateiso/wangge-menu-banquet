import { useState, useEffect, useRef } from 'react';
import { ConfigProvider, Input, Button, Card, Typography, message, theme } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import OrderForm from './components/OrderForm';
import MenuPreview from './components/MenuPreview';
import { login, generateMenu } from './api/menuApi';
import type { MenuRequest, MenuData } from './api/menuApi';

const { Title, Text } = Typography;

const appTheme = {
  token: {
    colorPrimary: '#8b5cf6',
    borderRadius: 12,
    fontFamily: "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', 'Segoe UI', sans-serif",
    colorBgContainer: 'rgba(255,255,255,0.85)',
    colorBorderSecondary: 'rgba(139,92,246,0.1)',
  },
  algorithm: theme.defaultAlgorithm,
};

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

    const timeout = new Promise<never>((_, reject) => {
      timerRef.current = setTimeout(() => reject(new Error('timeout')), 60000);
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
      <ConfigProvider locale={zhCN} theme={appTheme}>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            padding: 20,
          }}
        >
          <div className="animate-fade-in-up" style={{ width: '100%', maxWidth: 400 }}>
            <Card className="glass-card" style={{ padding: '20px 8px' }}>
              {/* Logo */}
              <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: 20,
                    background: 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 16,
                    boxShadow: '0 8px 24px rgba(139, 92, 246, 0.3)',
                  }}
                >
                  <span style={{ fontSize: 28, color: '#fff', fontWeight: 700 }}>旺</span>
                </div>
                <Title level={3} style={{ marginBottom: 4, color: '#1f2937', fontWeight: 700 }}>
                  旺阁渔村
                </Title>
                <Text style={{ color: '#9ca3af', fontSize: 14 }}>
                  AI 智能点菜系统
                </Text>
              </div>

              {/* 登录表单 */}
              <div style={{ padding: '0 8px' }}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#a78bfa' }} />}
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onPressEnter={handleLogin}
                  style={{
                    marginBottom: 20,
                    height: 48,
                    borderRadius: 14,
                    fontSize: 15,
                    border: '1px solid #e5e7eb',
                  }}
                  size="large"
                />
                <Button
                  type="primary"
                  block
                  size="large"
                  loading={loginLoading}
                  onClick={handleLogin}
                  className="btn-gradient"
                  style={{ height: 48, fontSize: 16 }}
                >
                  进入系统
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={zhCN} theme={appTheme}>
      <div style={{ minHeight: '100vh' }}>
        {/* Header */}
        <header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            padding: '12px 24px',
          }}
        >
          <div
            style={{
              maxWidth: 1400,
              margin: '0 auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(255, 255, 255, 0.7)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              borderRadius: 16,
              padding: '10px 24px',
              border: '1px solid rgba(255, 255, 255, 0.5)',
              boxShadow: '0 2px 12px rgba(139, 92, 246, 0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 8px rgba(139, 92, 246, 0.3)',
                }}
              >
                <span style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>旺</span>
              </div>
              <span style={{ fontWeight: 600, fontSize: 16, color: '#1f2937' }}>
                旺阁渔村
              </span>
              <span
                style={{
                  fontSize: 12,
                  color: '#9ca3af',
                  background: 'rgba(139, 92, 246, 0.08)',
                  padding: '2px 10px',
                  borderRadius: 20,
                  fontWeight: 500,
                }}
              >
                AI 智能点菜
              </span>
            </div>
            <Button
              type="text"
              size="small"
              style={{ color: '#9ca3af', fontWeight: 500 }}
              onClick={() => {
                localStorage.removeItem('wg_token');
                setAuthed(false);
                setMenu(null);
              }}
            >
              退出登录
            </Button>
          </div>
        </header>

        {/* Content */}
        <main style={{ padding: '16px 24px 40px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
          {!menu && !loading && (
            <div className="animate-fade-in-up">
              <OrderForm onSubmit={handleSubmit} loading={loading} />
            </div>
          )}

          {loading && (
            <div className="animate-fade-in" style={{ maxWidth: 500, margin: '60px auto' }}>
              <Card className="glass-card">
                <div className="loading-card">
                  <div
                    style={{
                      width: 56,
                      height: 56,
                      borderRadius: 16,
                      background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: 20,
                      boxShadow: '0 4px 16px rgba(139, 92, 246, 0.3)',
                    }}
                  >
                    <span style={{ fontSize: 24, color: '#fff', fontWeight: 700 }}>AI</span>
                  </div>
                  <Title level={4} style={{ marginBottom: 4, color: '#1f2937' }}>
                    正在为您智能配菜
                  </Title>
                  <Text style={{ color: '#9ca3af', fontSize: 14 }}>
                    根据您的需求搭配最佳菜品方案
                  </Text>
                  <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </Card>
            </div>
          )}

          {menu && (
            <div className="animate-fade-in-up">
              <MenuPreview
                menu={menu}
                onRegenerate={handleRegenerate}
                onMenuUpdated={(updated) => setMenu(updated)}
                loading={loading}
              />
              <div style={{ textAlign: 'center', marginTop: 20, marginBottom: 20 }}>
                <Button
                  type="text"
                  style={{ color: '#9ca3af', fontWeight: 500 }}
                  onClick={() => {
                    setMenu(null);
                    lastRequest.current = null;
                  }}
                >
                  返回重新下单
                </Button>
              </div>
            </div>
          )}
        </main>
      </div>
    </ConfigProvider>
  );
}

export default App;
