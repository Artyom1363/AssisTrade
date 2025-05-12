'use client'

import React, { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { popup } from '@telegram-apps/sdk'
import {
  useSendTransaction,
  useWaitForTransactionReceipt,
  useAccount,
  useConnect,
  type BaseError,
} from 'wagmi'
import { parseEther, type Address } from 'viem'
import { v4 as uuidv4 } from 'uuid'
import { injected } from 'wagmi/connectors'
import { miniApp } from '@telegram-apps/sdk'

// Определяем тип транзакции
type Transaction = {
  id: string
  to: string
  value: string
  token: string
  hash?: string
  status: 'rejected' | 'pending' | 'waiting' | 'success'
  error?: string
}

// Вспомогательная функция для форматирования адресов и хэшей
const formatAddress = (address: string | null | undefined): string => {
  if (!address) return '';
  return `${address.slice(0, 4)}...${address.slice(-4)}`;
};

// Create a client component for the transaction content
function TransactionContent() {
  const params = useSearchParams()
  const router = useRouter()

  // Подключение аккаунта
  const { address, isConnected } = useAccount()
  const { connect, isPending: isConnecting } = useConnect()

  // Параметры из URL
  const to = params.get('to')
  const value = params.get('value')
  const token = params.get('token')
  const urlId = params.get('id')

  // Определяем мобильное устройство
  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsMobile(/Mobi|Android|iPhone/i.test(navigator.userAgent))
    }
  }, [])

  // Генерация или установка ID транзакции
  const [id, setId] = useState<string>('')
  useEffect(() => {
    if (urlId) setId(urlId)
    else setId(uuidv4())
  }, [urlId])

  // Проверка параметров
  const [error, setError] = useState<string>()
  useEffect(() => {
    if (!to) setError('Missing recipient address')
    else if (!value) setError('Missing transaction amount')
    else if (!token) setError('Missing token information')
    else setError(undefined)
  }, [to, value, token])

  // Хук отправки транзакции
  const {
    data: hash,
    error: sendError,
    isPending,
    sendTransaction,
  } = useSendTransaction()

  // Хук ожидания подтверждения
  const {
    data: receipt,
    isLoading: isConfirming,
    isSuccess: isConfirmed,
    isError,
  } = useWaitForTransactionReceipt({ hash })

  // Попап Telegram на десктопе
  useEffect(() => {
    if (typeof window !== 'undefined' && !isMobile) {
      if (popup.isSupported()) {
        popup.open({
          title: 'Подтвердите транзакцию',
          message: 'Перейдите в кошёлёк Telegram для подписания',
          buttons: [{ id: 'ok', type: 'default', text: 'OK' }],
        }).then(btn => console.log('Popup:', btn))
      }
    }
  }, [isMobile])

  // Сохранение транзакции при появлении hash
  useEffect(() => {
    if (hash && id && to && value && token) {
      try {
        const stored: Transaction[] = JSON.parse(localStorage.getItem('txs') || '[]')
        const idx = stored.findIndex(t => t.id === id)
        const record: Transaction = { id, to, value, token, hash, status: 'pending' }
        if (idx >= 0) stored[idx] = { ...stored[idx], hash, status: 'pending' }
        else stored.push(record)
        localStorage.setItem('txs', JSON.stringify(stored))
      } catch (e) {
        console.error('LocalStorage error:', e)
      }
    }
  }, [hash, id, to, value, token])

  // Обработка ошибок отправки
  useEffect(() => {
    if (sendError && id) {
      try {
        const stored: Transaction[] = JSON.parse(localStorage.getItem('txs') || '[]')
        const idx = stored.findIndex(t => t.id === id)
        const msg = (sendError as BaseError).shortMessage || sendError.message
        if (idx >= 0) stored[idx] = { ...stored[idx], status: 'rejected', error: msg }
        else if (to && value && token)
          stored.push({ id, to, value, token, status: 'rejected', error: msg })
        localStorage.setItem('txs', JSON.stringify(stored))
      } catch (e) {
        console.error('LocalStorage error:', e)
      }
    }
  }, [sendError, id, to, value, token])

  // Навигация после подтверждения транзакции
  useEffect(() => {
    if (isConfirmed && receipt && id) {
      try {
        const stored: Transaction[] = JSON.parse(localStorage.getItem('txs') || '[]')
        const idx = stored.findIndex(t => t.id === id)
        if (idx >= 0) stored[idx] = { ...stored[idx], hash, status: 'waiting' }
        localStorage.setItem('txs', JSON.stringify(stored))
      } catch (e) {
        console.error('LocalStorage error:', e)
      }
      
      // Добавляем небольшую задержку, чтобы пользователь успел увидеть сообщение об успешной транзакции
      setTimeout(() => {
        try {
          window.close() // Закрываем окно
        } catch (e) {
          console.error('Could not close window:', e)
          router.push('/') // Альтернативное действие - перенаправление на главную
        }
      }, 1500)
    }
  }, [isConfirmed, receipt, id, hash, router])

  // Открыть Metamask на мобильных
  const openMetamaskWallet = () => {
    let redirected = false
    const mark = () => { redirected = true }
    const onVis = () => {
      if (document.hidden) { mark(); document.removeEventListener('visibilitychange', onVis) }
    }
    document.addEventListener('visibilitychange', onVis)
    try {
      const win = window.open('metamask://', '_blank')
      if (!win || win.closed) window.location.href = 'metamask://'
      else mark()
      setTimeout(() => { if (!redirected && !document.hidden) window.location.href = 'https://metamask.app.link/' }, 1500)
      setTimeout(() => {
        if (!redirected && !document.hidden) {
          document.removeEventListener('visibilitychange', onVis)
          if (confirm('Похоже, у вас не установлен Metamask. Установить?')) {
            window.open('https://metamask.io/download/', '_blank')
          }
        }
      }, 3000)
    } catch {
      window.open('https://metamask.io/download/', '_blank')
    }
  }

  // Обработчик подтверждения
  const onConfirm = () => {
    if (!to || !value || !token || !id) {
      setError('Missing required parameters')
      return
    }
    if (!isConnected) {
      connect({ connector: injected() })
      return
    }
    if (isMobile) {
      setTimeout(() => {
        sendTransaction({ to: to as Address, value: parseEther(value) })
      }, 1000)
      openMetamaskWallet()
    } else {
      sendTransaction({ to: to as Address, value: parseEther(value) })
    }
  }

  // Обработчик отклонения
  const onReject = () => {
    if (!id) return
    try {
      const stored: Transaction[] = JSON.parse(localStorage.getItem('txs') || '[]')
      const idx = stored.findIndex(t => t.id === id)
      if (idx >= 0) stored[idx] = { ...stored[idx], status: 'rejected' }
      else if (to && value && token) stored.push({ id, to, value, token, status: 'rejected' })
      localStorage.setItem('txs', JSON.stringify(stored))
    } catch (e) {
      console.error('Rejection error:', e)
    }
    window.close()
  }

  if (error) {
    return (
      <div className="p-4 space-y-4">
        <h2 className="text-lg text-red-600">Transaction Error</h2>
        <div>{error}</div>
        <button onClick={() => router.push('/')} className="px-4 py-2 rounded bg-blue-500 text-white">Back to Home</button>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-lg">Подтверждение транзакции</h2>
      <div>To: {formatAddress(to)}</div>
      <div>Amount: {value} {token}</div>
      <div>Transaction ID: {id}</div>
      {!isConnected && <div className="text-orange-600">Для отправки нужно подключить кошелёк</div>}
      {isMobile && isConnected && <div className="text-blue-600">Нажмите "Подтвердить" для Metamask</div>}
      {isConnected && <div className="text-green-600">Кошелёк: {formatAddress(address)}</div>}
      {sendError && <div className="text-red-600">Error: {(sendError as BaseError).shortMessage || sendError.message}</div>}
      <div className="flex gap-2">
        <button onClick={onReject} disabled={isPending || isConfirming} className="px-4 py-2 bg-red-500 rounded text-white">Отклонить</button>
        <button onClick={onConfirm} disabled={isPending || isConfirming} className="px-4 py-2 bg-green-500 rounded text-white">
          {isConnecting ? 'Подключение...' : isPending ? 'Подпись...' : isConfirming ? 'Отправка...' : 'Подтвердить'}
        </button>
      </div>
      {hash && <div>Transaction Hash: {formatAddress(hash)}</div>}
      {isConfirming && <div>Waiting for confirmation...</div>}
      {isConfirmed && <div className="text-green-600">Transaction confirmed!</div>}
      {isError && <div className="text-red-600">Error confirming transaction</div>}
    </div>
  )
}

// Main page component with Suspense
export default function TxPage() {
  return (
    <Suspense fallback={<div className="p-4">Loading transaction details...</div>}>
      <TransactionContent />
    </Suspense>
  )
}
