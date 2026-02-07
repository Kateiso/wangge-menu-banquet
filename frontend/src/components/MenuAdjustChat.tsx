import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Space, Spin, message } from 'antd';
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
        // 标记已确认
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
      title="调整菜单"
      size="small"
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: '8px 12px', overflow: 'hidden' } }}
    >
      {/* 消息列表 */}
      <div
        ref={listRef}
        style={{ flex: 1, overflowY: 'auto', marginBottom: 8 }}
      >
        {messages.length === 0 && (
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: '20px 0' }}>
            输入需求调整菜单，如"换掉凉菜"、"加个海鲜"
          </Text>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: 8,
            }}
          >
            <div
              style={{
                maxWidth: '85%',
                padding: '8px 12px',
                borderRadius: 8,
                background: msg.role === 'user' ? '#1677ff' : '#f5f5f5',
                color: msg.role === 'user' ? '#fff' : '#333',
                fontSize: 13,
              }}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              {msg.type === 'suggest' && !msg.confirmed && msg.conversationId && (
                <div style={{ marginTop: 6, textAlign: 'right' }}>
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckOutlined />}
                    loading={confirming === msg.conversationId}
                    onClick={() => handleConfirm(msg.conversationId!, i)}
                  >
                    确认调整
                  </Button>
                </div>
              )}
              {msg.confirmed && (
                <div style={{ marginTop: 4 }}>
                  <Text type="success" style={{ fontSize: 12 }}>已确认</Text>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ textAlign: 'center', padding: 8 }}>
            <Space><Spin size="small" /><Text type="secondary">AI 思考中...</Text></Space>
          </div>
        )}
      </div>

      {/* 输入框 */}
      <Input
        placeholder="输入调整需求..."
        value={input}
        onChange={e => setInput(e.target.value)}
        onPressEnter={handleSend}
        disabled={loading}
        suffix={
          <Button
            type="text"
            size="small"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!input.trim() || loading}
          />
        }
      />
    </Card>
  );
}
