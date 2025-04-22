'use client'

import React, { useEffect, useState } from 'react'
import { miniApp } from '@telegram-apps/sdk'

export function TelegramProvider({ children }: { children: React.ReactNode }) {
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const MAX_RETRIES = 3;

  useEffect(() => {
    // Обнаружение, запущены ли мы в браузере
    const isBrowser = typeof window !== 'undefined';
    
    // Обнаружение, запущены ли мы внутри Telegram WebView
    const isTelegramWebView = isBrowser && 
      (window.Telegram?.WebApp || 
       navigator.userAgent.includes('TelegramWebApp') ||
       window.location.search.includes('tgWebAppData='));
    
    // Function to initialize the Mini App with error handling
    const initializeMiniApp = async () => {
      // Если мы не в Telegram WebView, пропускаем инициализацию Telegram SDK
      if (!isTelegramWebView) {
        console.log('Not running inside Telegram WebView, skipping Telegram SDK initialization');
        return;
      }
      
      try {
        // Оборачиваем каждый вызов в отдельный try-catch
        
        try {
          // Монтируем компонент miniApp
          if (miniApp.mountSync && miniApp.mountSync.isAvailable()) {
            miniApp.mountSync();
          }
        } catch (e) {
          console.warn('Error mounting Telegram Mini App:', e);
        }

        try {
          // Привязываем CSS переменные для использования цветов темы в стилях
          if (miniApp.bindCssVars && miniApp.bindCssVars.isAvailable()) {
            miniApp.bindCssVars();
          }
        } catch (e) {
          console.warn('Error binding CSS vars:', e);
        }

        try {
          // Даём знать Telegram, что приложение готово
          if (miniApp.ready && miniApp.ready.isAvailable()) {
            miniApp.ready();
          }
        } catch (e) {
          console.warn('Error setting ready state:', e);
        }

        try {
          // Устанавливаем цвет фона
          if (miniApp.setBackgroundColor && miniApp.setBackgroundColor.isAvailable()) {
            const bgColor = miniApp.backgroundColor() || '#ffffff';
            miniApp.setBackgroundColor(bgColor);
          }
        } catch (e) {
          console.warn('Error setting background color:', e);
        }

        try {
          // Устанавливаем цвет шапки
          if (miniApp.setHeaderColor && 
              miniApp.setHeaderColor.isAvailable() && 
              miniApp.setHeaderColor.supports && 
              miniApp.setHeaderColor.supports['rgb']) {
            const headerColor = '#0088cc';
            miniApp.setHeaderColor(headerColor);
          }
        } catch (e) {
          console.warn('Error setting header color:', e);
        }

        // Clear any previous errors if connection succeeds
        setConnectionError(null);
        setRetryCount(0);
      } catch (error) {
        // Handle and store the error
        const errorMessage = error instanceof Error ? error.message : 'Unknown connection error';
        setConnectionError(errorMessage);
        
        // Only retry a limited number of times
        if (retryCount < MAX_RETRIES) {
          console.log(`Retry attempt ${retryCount + 1} of ${MAX_RETRIES}`);
          setRetryCount(count => count + 1);
          setTimeout(initializeMiniApp, 3000);
        } else {
          console.error('Maximum retry attempts reached. Continuing without Telegram features.');
        }
        
        console.error('Telegram Mini App initialization error:', error);
      }
    };

    // Start initialization
    initializeMiniApp();

    // Размонтируем при удалении компонента
    return () => {
      if (isTelegramWebView) {
        try {
          if (miniApp.unmount) {
            miniApp.unmount();
          }
        } catch (error) {
          console.error('Error unmounting Telegram Mini App:', error);
        }
      }
    };
  }, [retryCount]);

  // For non-critical errors, show the app with an error notification
  if (connectionError && retryCount >= MAX_RETRIES) {
    return (
      <>
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#fff3cd', 
          color: '#664d03',
          border: '1px solid #ffecb5',
          borderRadius: '4px',
          margin: '10px 0',
          fontSize: '14px' 
        }}>
          <p><strong>Примечание:</strong> Некоторые функции Telegram недоступны.</p>
          <p style={{ fontSize: '12px' }}>{connectionError}</p>
        </div>
        {children}
      </>
    );
  }

  return <>{children}</>;
}