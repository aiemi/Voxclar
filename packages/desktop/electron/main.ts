/**
 * Voxclar Electron 主进程
 *
 * 关键特性：
 * 1. 主窗口 + 悬浮字幕窗口（双窗口）
 * 2. 屏幕共享保护 — Zoom/Teams/Meet 投屏时隐藏本应用
 * 3. 自动启动 Python 本地引擎
 * 4. macOS 原生集成（交通灯按钮、dock 菜单）
 */
import { app, BrowserWindow, ipcMain, screen, systemPreferences, nativeImage } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import path from 'path'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const VITE_URL = 'http://localhost:5173'

let mainWindow: BrowserWindow | null = null
let captionWindow: BrowserWindow | null = null
let engineProcess: ChildProcess | null = null

// App icon
const getAppIcon = () => {
  const iconPath = path.join(__dirname, '../icon.icns')
  try { return nativeImage.createFromPath(iconPath) } catch { return undefined }
}

// ═══════════════════════════════════════════════════════════════════
// 窗口创建
// ═══════════════════════════════════════════════════════════════════

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1000,
    minHeight: 700,
    titleBarStyle: 'hiddenInset', // macOS 交通灯按钮内嵌
    trafficLightPosition: { x: 12, y: 10 },
    backgroundColor: '#000000',
    icon: getAppIcon(),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  if (isDev) {
    mainWindow.loadURL(VITE_URL)
    // mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // 窗口准备好再显示，避免白屏闪烁
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
    // 应用屏幕共享保护
    setWindowSharingProtection(mainWindow!)
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    captionWindow?.close()
  })
}

function createCaptionWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize

  captionWindow = new BrowserWindow({
    width: 700,
    height: 320,
    x: Math.round((screenWidth - 700) / 2), // 屏幕底部居中
    y: screenHeight - 360,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    movable: true,
    hasShadow: false,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  if (isDev) {
    captionWindow.loadURL(`${VITE_URL}/#/caption`)
  } else {
    captionWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: '/caption' })
  }

  captionWindow.once('ready-to-show', () => {
    // 应用屏幕共享保护 — 悬浮窗更需要隐藏
    setWindowSharingProtection(captionWindow!)
  })

  // 设置窗口层级 — 在 Zoom 等应用之上
  captionWindow.setAlwaysOnTop(true, 'screen-saver')

  captionWindow.on('closed', () => {
    captionWindow = null
  })
}

// ═══════════════════════════════════════════════════════════════════
// 屏幕共享保护 — Zoom/Teams/Meet 投屏时不可见
// ═══════════════════════════════════════════════════════════════════

function setWindowSharingProtection(win: BrowserWindow) {
  /**
   * 核心安全功能：
   * - macOS: setContentProtection(true) → 等同于 NSWindowSharingNone
   *   当用户在 Zoom/Teams/Meet 中共享屏幕时，本应用的窗口内容
   *   会被替换为黑色/空白，其他参会者看不到 AI 回答
   * - Windows: setContentProtection(true) → 使用 SetWindowDisplayAffinity
   *   同样效果，阻止截屏和录屏
   */
  win.setContentProtection(true)

  // macOS: 额外通过 native API 设置 window sharing 属性
  if (process.platform === 'darwin') {
    // Electron 的 setContentProtection 在 macOS 上已经调用了
    // NSWindow.sharingType = .none，这是最强的保护级别
    // 截屏、录屏、屏幕共享都会显示黑色
    console.log('[Security] Window content protection enabled (NSWindowSharingNone)')
  } else if (process.platform === 'win32') {
    console.log('[Security] Window content protection enabled (SetWindowDisplayAffinity)')
  }
}

// ═══════════════════════════════════════════════════════════════════
// Python 本地引擎管理
// ═══════════════════════════════════════════════════════════════════

function startEngine() {
  const enginePath = path.join(__dirname, '../../local-engine')

  // 尝试用 poetry run，fallback 到直接 python
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
  engineProcess = spawn(pythonCmd, ['-m', 'src.server'], {
    cwd: enginePath,
    stdio: 'pipe',
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  })

  engineProcess.stdout?.on('data', (data: Buffer) => {
    const msg = data.toString().trim()
    console.log(`[Engine] ${msg}`)
    // 转发引擎日志到渲染进程
    mainWindow?.webContents.send('engine:log', msg)
  })

  engineProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[Engine] ${data.toString().trim()}`)
  })

  engineProcess.on('exit', (code: number | null) => {
    console.log(`[Engine] Process exited with code ${code}`)
    engineProcess = null
    mainWindow?.webContents.send('engine:status', 'disconnected')
  })

  engineProcess.on('error', (err: Error) => {
    console.error(`[Engine] Failed to start: ${err.message}`)
    mainWindow?.webContents.send('engine:error', err.message)
  })
}

function stopEngine() {
  if (engineProcess) {
    engineProcess.kill('SIGTERM')
    // 3秒后强制杀
    setTimeout(() => {
      if (engineProcess) {
        engineProcess.kill('SIGKILL')
        engineProcess = null
      }
    }, 3000)
  }
}

// ═══════════════════════════════════════════════════════════════════
// IPC 处理
// ═══════════════════════════════════════════════════════════════════

// 窗口控制
ipcMain.handle('window:minimize', () => mainWindow?.minimize())
ipcMain.handle('window:maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize()
  else mainWindow?.maximize()
})
ipcMain.handle('window:close', () => mainWindow?.close())

// 悬浮字幕窗口控制
ipcMain.handle('caption:show', () => {
  if (!captionWindow) createCaptionWindow()
  else captionWindow.show()
})
ipcMain.handle('caption:hide', () => captionWindow?.hide())
ipcMain.handle('caption:toggle', () => {
  if (captionWindow?.isVisible()) {
    captionWindow.hide()
  } else {
    if (!captionWindow) createCaptionWindow()
    else captionWindow.show()
  }
  return captionWindow?.isVisible() ?? false
})

// 字幕内容推送到悬浮窗
ipcMain.handle('caption:update', (_event, data) => {
  captionWindow?.webContents.send('caption:data', data)
})

// 悬浮窗透明度调整
ipcMain.handle('caption:setOpacity', (_event, opacity: number) => {
  if (captionWindow) {
    captionWindow.setOpacity(Math.max(0.1, Math.min(1, opacity)))
  }
})

// 获取屏幕共享保护状态
ipcMain.handle('security:getStatus', () => ({
  contentProtection: true,
  platform: process.platform,
}))

// ═══════════════════════════════════════════════════════════════════
// 应用生命周期
// ═══════════════════════════════════════════════════════════════════

app.whenReady().then(() => {
  // macOS Dock icon
  if (process.platform === 'darwin') {
    const icon = getAppIcon()
    if (icon && !icon.isEmpty()) {
      app.dock.setIcon(icon)
      console.log('[Icon] Dock icon set successfully')
    } else {
      console.log('[Icon] Failed to load icon from:', path.join(__dirname, '../icon.icns'))
    }
  }

  createMainWindow()
  startEngine()

  // 悬浮字幕窗口不再自动创建 — 由会议开始时通过 caption:show IPC 触发

  // macOS: 检查屏幕录制权限（ScreenCaptureKit 需要）
  if (process.platform === 'darwin') {
    const hasScreenAccess = systemPreferences.getMediaAccessStatus('screen')
    console.log(`[Permission] Screen recording: ${hasScreenAccess}`)
  }
})

app.on('before-quit', () => {
  stopEngine()
})

app.on('window-all-closed', () => {
  stopEngine()
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (!mainWindow) createMainWindow()
})
