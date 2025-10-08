import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Sparkles, RotateCcw, MessageCircle, ChevronDown, ChevronUp } from 'lucide-react';
import Chart from './components/Chart';
import Table from './components/Table';
import '@/App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [treePath, setTreePath] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    initializeChat();
  }, []);

  const initializeChat = async () => {
    try {
      setIsInitializing(true);
      const response = await axios.post(`${API}/chat/initialize`, {});
      setSessionId(response.data.session_id);
      setSuggestions(response.data.suggestions);
      setMessages([{
        role: 'assistant',
        content: 'Welcome! I\'m your intelligent data assistant. I can help you explore and understand your Quality Control and Manufacturing Management database. Choose a suggestion below or ask me anything!',
        timestamp: new Date().toISOString()
      }]);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error initializing chat:', error);
    } finally {
      setIsInitializing(false);
    }
  };

  const sendMessage = async (message, isSuggestion = false) => {
    if (!message.trim() || !sessionId) return;

    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setShowSuggestions(false);

    try {
      const response = await axios.post(`${API}/chat/message`, {
        session_id: sessionId,
        message: message,
        is_suggestion: isSuggestion
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        metadata: response.data.metadata,
        chartData: response.data.chart_data,
        tableData: response.data.table_data
      };

      setMessages(prev => [...prev, assistantMessage]);
      setSuggestions(response.data.suggestions);
      setTreePath(response.data.context_path);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion, true);
  };

  const handleReset = () => {
    initializeChat();
    setMessages([]);
    setTreePath([]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      sendMessage(inputValue, false);
    }
  };

  if (isInitializing) {
    return (
      <div className="app-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Initializing chatbot...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <div className="header-icon-wrapper">
              <MessageCircle className="header-icon" />
            </div>
            <div>
              <h1 className="header-title">Data Intelligence Bot</h1>
              <p className="header-subtitle">Explore your database with AI-powered insights</p>
            </div>
          </div>
          <button 
            onClick={handleReset} 
            className="reset-button"
            data-testid="reset-button"
          >
            <RotateCcw size={18} />
            <span>New Chat</span>
          </button>
        </div>
      </header>

      {/* Decision Tree Breadcrumb */}
      {treePath.length > 0 && (
        <div className="tree-path-container">
          <div className="tree-path">
            <span className="tree-path-label">Path:</span>
            {treePath.slice(-3).map((item, index) => (
              <React.Fragment key={index}>
                <span className="tree-path-item">
                  {item.length > 50 ? item.substring(0, 50) + '...' : item}
                </span>
                {index < Math.min(treePath.length, 3) - 1 && (
                  <span className="tree-path-arrow">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        <div className="content-wrapper">
          {/* Messages Section */}
          <div className="messages-section">
            <div className="messages-container" data-testid="messages-container">
              {messages.map((msg, index) => (
                <div 
                  key={index} 
                  className={`message ${msg.role}`}
                  data-testid={`message-${msg.role}`}
                >
                  <div className="message-content">
                    {msg.role === 'assistant' && (
                      <div className="message-avatar assistant-avatar">
                        <Sparkles size={16} />
                      </div>
                    )}
                    <div className="message-bubble">
                      <p>{msg.content}</p>
                      {msg.chartData && (
                        <div className="message-chart">
                          <Chart chartData={msg.chartData} />
                        </div>
                      )}
                      {msg.tableData && (
                        <div className="message-table">
                          <Table tableData={msg.tableData} />
                        </div>
                      )}
                      {msg.metadata?.relevant_tables && msg.metadata.relevant_tables.length > 0 && (
                        <div className="message-metadata">
                          <small>📊 Referenced: {msg.metadata.relevant_tables.join(', ')}</small>
                        </div>
                      )}
                    </div>
                    {msg.role === 'user' && (
                      <div className="message-avatar user-avatar">You</div>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="message assistant" data-testid="loading-indicator">
                  <div className="message-content">
                    <div className="message-avatar assistant-avatar">
                      <Sparkles size={16} />
                    </div>
                    <div className="message-bubble loading-bubble">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Suggestions Panel */}
          {suggestions.length > 0 && (
            <div className={`suggestions-panel ${showSuggestions ? 'visible' : 'hidden'}`}>
              <div className="suggestions-header">
                <div className="suggestions-header-content">
                  <Sparkles size={16} className="suggestions-header-icon" />
                  <span className="suggestions-title">Suggested Questions</span>
                  <span className="suggestions-count">{suggestions.length}</span>
                </div>
                <button 
                  className="suggestions-toggle"
                  onClick={() => setShowSuggestions(!showSuggestions)}
                  data-testid="toggle-suggestions"
                >
                  {showSuggestions ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
                </button>
              </div>
              
              {showSuggestions && (
                <div className="suggestions-content">
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="suggestion-card"
                      disabled={isLoading}
                      data-testid={`suggestion-${index}`}
                    >
                      <div className="suggestion-number">{index + 1}</div>
                      <span className="suggestion-text">{suggestion}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="input-container">
          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask me anything about your database..."
              className="input-field"
              disabled={isLoading}
              data-testid="message-input"
            />
            <button 
              type="submit" 
              className="send-button" 
              disabled={isLoading || !inputValue.trim()}
              data-testid="send-button"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
