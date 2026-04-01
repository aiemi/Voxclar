import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  // 窗口控制（frameless window）
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
  },

  // 悬浮字幕窗口控制
  caption: {
    show: () => ipcRenderer.invoke('caption:show'),
    hide: () => ipcRenderer.invoke('caption:hide'),
    toggle: () => ipcRenderer.invoke('caption:toggle'),
    update: (data: unknown) => ipcRenderer.invoke('caption:update', data),
    setOpacity: (opacity: number) => ipcRenderer.invoke('caption:setOpacity', opacity),
    // 悬浮窗接收字幕数据
    onData: (callback: (data: unknown) => void) => {
      ipcRenderer.on('caption:data', (_event, data) => callback(data))
      return () => ipcRenderer.removeAllListeners('caption:data')
    },
  },

  // 引擎状态
  engine: {
    onLog: (callback: (msg: string) => void) => {
      ipcRenderer.on('engine:log', (_event, msg) => callback(msg))
      return () => ipcRenderer.removeAllListeners('engine:log')
    },
    onStatus: (callback: (status: string) => void) => {
      ipcRenderer.on('engine:status', (_event, status) => callback(status))
      return () => ipcRenderer.removeAllListeners('engine:status')
    },
    onError: (callback: (error: string) => void) => {
      ipcRenderer.on('engine:error', (_event, error) => callback(error))
      return () => ipcRenderer.removeAllListeners('engine:error')
    },
  },

  // 安全状态
  security: {
    getStatus: () => ipcRenderer.invoke('security:getStatus'),
  },

  // 平台信息
  platform: process.platform,
})
