import React, { useState, useRef, useEffect } from 'react';

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    try {
        setIsLoading(true);
        const userMessage = {
            type: 'user',
            content: inputMessage,
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessage]);
        setInputMessage('');

        const response = await fetch('http://127.0.0.1:5000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: inputMessage })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to get response');
        }

        const assistantMessage = {
            type: 'assistant',
            content: data.message,
            sources: data.sources,
            used_context: data.used_context,
            context_preview: data.context_preview,
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
        console.error('Chat error:', error);
        const errorMessage = {
            type: 'error',
            content: 'Sorry, there was an error processing your request.',
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMessage]);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      <div className="p-4 border-b">
        <h1 className="text-xl font-semibold">PTRS:6224 Course Assistant</h1>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.type === 'user'
                  ? 'bg-blue-500 text-white'
                  : message.type === 'error'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="text-sm">{message.content}</p>
              {message.type === 'assistant' && (
                <div className="mt-2 text-xs text-gray-600">
                  {message.used_context && (
                    <div className="mb-1">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                        Using Course Materials
                      </span>
                    </div>
                  )}
                  {message.sources && message.sources.filename && (
                    <p className="mb-1">
                      📄 Source: {message.sources.filename}
                    </p>
                  )}
                  {message.context_preview && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-blue-600 hover:text-blue-700">
                        View Reference Context
                      </summary>
                      <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-700">
                        {message.context_preview}...
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask a question about the course..."
            disabled={isLoading}
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50 hover:bg-blue-600 transition-colors"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatContainer;