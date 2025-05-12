'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePublicClient } from 'wagmi'

export type Tx = {
  id: string
  to: string
  value: string
  token: string
  hash?: string
  status: 'rejected' | 'pending' | 'waiting' | 'success'
}

export function TransactionsList({ address }: { address: string }) {
  const [txs, setTxs] = useState<Tx[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const publicClient = usePublicClient()

  // Helper function to truncate addresses
  const truncateAddress = (address: string) => {
    if (!address || address.length < 9) return address;
    return `${address.substring(0, 4)}...${address.substring(address.length - 4)}`;
  };

  // Безопасное чтение из localStorage
  const safeGetFromStorage = () => {
    try {
      if (typeof window === 'undefined' || !window.localStorage) {
        console.warn('localStorage is not available');
        return [];
      }
      
      const stored = localStorage.getItem('txs');
      if (!stored) return [];
      
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      console.error('Error reading from localStorage:', err);
      setLoadError('Failed to load transaction history');
      return [];
    }
  };

  // Безопасная запись в localStorage
  const safeSetToStorage = (data: Tx[]) => {
    try {
      if (typeof window === 'undefined' || !window.localStorage) {
        console.warn('localStorage is not available');
        return;
      }
      
      localStorage.setItem('txs', JSON.stringify(data));
    } catch (err) {
      console.error('Error writing to localStorage:', err);
      setLoadError('Failed to save transaction data');
    }
  };

  // Загрузка транзакций при монтировании компонента
  useEffect(() => {
    console.log('Loading transactions for address:', address);
    const transactions = safeGetFromStorage();
    console.log('Loaded transactions:', transactions);
    // Сортируем транзакции так, чтобы новые были вверху (в обратном порядке)
    setTxs([...transactions].reverse());
  }, [address]);

  // Функция для обновления статуса транзакции
  const updateTransactionStatus = (txId: string, status: Tx['status']) => {
    setTxs(prevTxs => {
      const newTxs = prevTxs.map(tx => 
        tx.id === txId ? { ...tx, status } : tx
      );
      
      // Не перезаписываем localStorage здесь, это будет сделано в useEffect
      return newTxs;
    });
  };

  // Отслеживание статусов транзакций, находящихся в состоянии pending или waiting
  useEffect(() => {
    if (!publicClient) {
      console.log('PublicClient not available yet');
      return;
    }

    const pendingTxs = txs.filter(tx => 
      (tx.status === 'pending' || tx.status === 'waiting') && tx.hash
    );
    
    console.log('Transactions to monitor:', pendingTxs.length, pendingTxs);
    
    if (pendingTxs.length === 0) return;
    
    console.log('Pending transactions to monitor:', pendingTxs);
    
    // Функция для проверки статуса одной транзакции
    const checkTransaction = async (tx: Tx) => {
      if (!tx.hash) return;
      
      try {
        const receipt = await publicClient.getTransactionReceipt({
          hash: tx.hash as `0x${string}`,
        });
        
        // Ethereum возвращает статус как number (1 = success, 0 = failed)
        if (receipt) {
          console.log('Transaction receipt received:', tx.id, receipt);
          
          // Проверяем статус правильно (в Ethereum 1 = успех)
          if (receipt.status === "success") {
            console.log('Transaction confirmed successfully:', tx.id);
            updateTransactionStatus(tx.id, 'success');
          }
        }
      } catch (err) {
        console.error('Error checking transaction status:', err, tx.hash);
      }
    };
    
    // Проверяем статус каждой ожидающей транзакции
    const checkAllPendingTransactions = async () => {
      for (const tx of pendingTxs) {
        await checkTransaction(tx);
      }
    };
    
    // Выполняем первую проверку сразу
    checkAllPendingTransactions();
    
    // Затем настраиваем интервал для периодических проверок
    const intervalId = setInterval(checkAllPendingTransactions, 15000); // каждые 15 секунд
    
    return () => clearInterval(intervalId);
  }, [txs, publicClient]);

  // Сохранение транзакций при их изменении
  useEffect(() => {
    if (txs.length > 0) {
      console.log('Saving transactions:', txs);
      // При сохранении всего списка транзакций мы должны инвертировать порядок,
      // чтобы в localStorage они хранились в исходном порядке
      safeSetToStorage([...txs].reverse());
    }
  }, [txs]);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Транзакции</h2>
      
      {loadError && (
        <div className="p-2 bg-red-100 border border-red-300 rounded text-red-800">
          {loadError}
        </div>
      )}
      
      <div className="space-y-2">
        {txs.length === 0 ? (
          <p>У вас пока нет транзакций</p>
        ) : (
          txs.map(tx => (
            <div
              key={tx.id}
              className="p-3 border rounded flex justify-between items-center"
            >
              <div>
                <div>To: {truncateAddress(tx.to)}</div>
                <div>
                  Amount: {tx.value} {tx.token}
                </div>
                {tx.hash && <div className="text-xs text-gray-500">Hash: {truncateAddress(tx.hash)}</div>}
              </div>
              <div className="space-x-2">
                {tx.status !== 'rejected' ? (
                  <Link
                    href={
                      tx.hash
                        ? `https://etherscan.io/tx/${tx.hash}`
                        : `/transaction?to=${tx.to}&value=${tx.value}&token=${tx.token}&id=${tx.id}`
                    }
                    className={`px-2 py-1 rounded ${
                      tx.status === 'pending'
                        ? 'bg-yellow-200'
                        : tx.status === 'waiting'
                        ? 'bg-blue-200'
                        : 'bg-green-200'
                    }`}
                  >
                    {tx.status}
                  </Link>
                ) : (
                  <span className="px-2 py-1 rounded bg-red-200">rejected</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Debug section */}
      {process.env.NODE_ENV !== 'production' && (
        <div className="mt-8 p-3 bg-gray-100 text-xs">
          <p>Debug info:</p>
          <p>Address: {address}</p>
          <p>Transactions count: {txs.length}</p>
          <p>localStorage available: {typeof window !== 'undefined' && !!window.localStorage ? 'Yes' : 'No'}</p>
          <p>Pending/Waiting transactions: {txs.filter(tx => tx.status === 'pending' || tx.status === 'waiting').length}</p>
        </div>
      )}
    </div>
  )
}