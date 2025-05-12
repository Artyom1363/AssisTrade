'use client'

import { WagmiProvider, createConfig, http } from 'wagmi'
import { mainnet, sepolia } from 'wagmi/chains'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConnectKitProvider, getDefaultConfig } from 'connectkit'
import { useEffect, useState } from 'react'

// Создаем конфигурацию с расширенными опциями
const createWagmiConfig = () => {
  return createConfig(
    getDefaultConfig({
      chains: [mainnet, sepolia],
      transports: {
        [mainnet.id]: http(
          `https://mainnet.infura.io/v3/${process.env.NEXT_PUBLIC_INFURA_ID}`
        ),
        [sepolia.id]: http(
          `https://sepolia.infura.io/v3/${process.env.NEXT_PUBLIC_INFURA_ID}`
        ),
      },
      walletConnectProjectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || '',
      appName: 'Telegram Mini App',
      appDescription: 'Mini DApp inside Telegram',
      appUrl: typeof window !== 'undefined' ? window.location.origin : '',
      appIcon: 'https://your-icon-url.png',
    })
  )
}

export function Web3Provider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<any>(null)
  const [queryClient] = useState(() => new QueryClient())

  useEffect(() => {
    // Инициализируем конфигурацию только на стороне клиента
    setConfig(createWagmiConfig())
    
    // Добавляем обработчик для возвращения из MetaMask
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Можно добавить логику для обновления соединения
        console.log('App visibility restored, checking connection status...')
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  if (!config) return null // Ждем инициализации конфигурации

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <ConnectKitProvider 
          options={{
            hideNoWalletCTA: true,
            embedGoogleFonts: true,
            walletConnectCTA: 'both',
          }}
        >
          {children}
        </ConnectKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  )
}