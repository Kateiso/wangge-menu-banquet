import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Spin, message } from 'antd';
import { SendOutlined, CheckOutlined } from '@ant-design/icons';
import { adjustMenu } from '../api/menuApi';
import type { MenuData, AdjustAction } from '../api/menuApi';

const { Text } = Typography;

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  type?: 'ask' | 'suggest' | 'updated';
  action?: AdjustAction | null;
  conversationId?: number | null;
  confirmed?: boolean;
}

interface Props {
  menuId: string;
  onMenuUpdated: (menu: MenuData) => void;
}

export default function MenuAdjustChat({ menuId, onMenuUpdated }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await adjustMenu(menuId, text, 'chat');
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: res.message,
          type: res.type as ChatMessage['type'],
          action: res.action,
          conversationId: res.conversation_id,
        },
      ]);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '请求失败');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (conversationId: number, msgIndex: number) => {
    setConfirming(conversationId);
    try {
      const res = await adjustMenu(menuId, '', 'confirm', conversationId);
      if (res.type === 'updated' && res.menu) {
        onMenuUpdated(res.menu);
        setMessages(prev =>
          prev.map((m, i) => (i === msgIndex ? { ...m, confirmed: true } : m))
        );
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: '菜单已更新', type: 'updated' },
        ]);
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : '确认失败');
    } finally {
      setConfirming(null);
    }
  };

  return (
    <Card
      className="glass-card"
      styles={{
        header: {
          borderBottom: '1px solid rgba(139, 92, 246, 0.08)',
          padding: '14px 20px',
          minHeight: 'auto',
        },
        body: {
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          height: 'calc(100% - 52px)',
          overflow: 'hidden',
        },
      }}
      title={
        <span style={{ fontWeight: 600, color: '#1f2937', fontSize: 15 }}>
          调整菜单
        </span>
      }
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      {/* 消息列表 */}
      <div
        ref={listRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 16px 8px',
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              padding: '40px 16px',
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 14,
                background: 'rgba(139, 92, 246, 0.08)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 12,
              }}
            >
              <span style={{ fontSize: 18, color: '#8b5cf6' }}>AI</span>
            </div>
            <Text
              style={{
                display: 'block',
                color: '#9ca3af',
                fontSize: 13,
                lineHeight: 1.6,
              }}
            >
              说出你的想法，AI 帮你调整
              <br />
              如"虾不要了"、"加个青菜"、"贵了便宜点"
            </Text>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className="animate-fade-in"
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: 12,
            }}
          >
            <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              {msg.type === 'suggest' && !msg.confirmed && msg.conversationId && (
                <div style={{ marginTop: 8, textAlign: 'right' }}>
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckOutlined />}
                    loading={confirming === msg.conversationId}
                    onClick={() => handleConfirm(msg.conversationId!, i)}
                    className="btn-gradient"
                    style={{
                      borderRadius: 8,
                      fontSize: 12,
                      height: 28,
                    }}
                  >
                    确认调整
                  </Button>
                </div>
              )}
              {msg.confirmed && (
                <div style={{ marginTop: 6 }}>
                  <span style={{ fontSize: 12, color: '#10b981', fontWeight: 500 }}>
                    已确认
                  </span>
                </div>
              )}
              {msg.type === 'updated' && (
                <span
                  style={{
                    display: 'inline-block',
                    marginTop: 4,
                    background: 'rgba(16, 185, 129, 0.1)',
                    color: '#10b981',
                    padding: '2px 8px',
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  已生效
                </span>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="animate-fade-in" style={{ textAlign: 'center', padding: '8px 0' }}>
            <Spin size="small" />
            <Text style={{ color: '#9ca3af', fontSize: 12, marginLeft: 8 }}>
              AI 思考中...
            </Text>
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid rgba(139, 92, 246, 0.06)',
        }}
      >
        <Input
          placeholder="输入调整需求..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onPressEnter={handleSend}
          disabled={loading}
          style={{
            borderRadius: 12,
            border: '1px solid #e5e7eb',
            fontSize: 14,
          }}
          suffix={
            <Button
              type="text"
              size="small"
              icon={<SendOutlined style={{ color: input.trim() ? '#8b5cf6' : '#d1d5db' }} />}
              onClick={handleSend}
              disabled={!input.trim() || loading}
              style={{ cursor: 'pointer' }}
            />
          }
        />
      </div>
    </Card>
  );
}
