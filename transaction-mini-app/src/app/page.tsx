'use client'

import { ConnectKitButton } from 'connectkit'
import { useAccount } from 'wagmi'
import { TransactionsList } from '../components/TransactionsList'
import { Web3Provider } from './web3-provider'

export default function HomePage() {
  const { address, isConnecting, isDisconnected } = useAccount()

  if (isConnecting) return <div>Подключение кошелька...</div>
  if (isDisconnected) {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <h1 className="text-xl mb-4">Добро пожаловать в DApp внутри Telegram!</h1>
        <ConnectKitButton />
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex justify-end">
        <ConnectKitButton showBalance={false} />
      </div>
      <TransactionsList address={address!} />
    </div>
  )
}
