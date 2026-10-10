import request from '@/utils/request'

export interface SysHealth {
  backend: 'ok' | 'error'
  ffmpeg: 'ok' | 'missing'
  db: 'ok' | 'error'
  whisper_model: {
    /** 当前选中的模型 size，例如 'tiny' / 'base' / 'large-v3' */
    size: string | null
    /** 转写器类型 */
    type: string | null
    /** 是否已完整下载到本地（仅本地引擎有意义） */
    downloaded: boolean
    /** 是否实际检查过 —— 在线引擎跳过检查时为 false */
    checked: boolean
  }
}

/** 详细健康状态：用于设置页 / 启动诊断。后端始终返回 200，按字段判断各项。 */
export const getSysHealth = async (): Promise<SysHealth> => {
  return await request.get('/sys_health')
}

/** 保留旧 systemCheck 函数名（App.tsx 启动时仍调用），返回值同 getSysHealth。 */
export const systemCheck = getSysHealth

export interface DeployStatus {
  backend: {
    status: string
    port: number
  }
  cuda: {
    available: boolean
    /** 新增：torch 是否安装。轻量部署没装 torch 时为 false，避免误判为 CUDA 故障 */
    torch_installed?: boolean
    version: string | null
    gpu_name: string | null
  }
  whisper: {
    model_size: string
    transcriber_type: string
    /** 新增：模型是否已完整下载（fast-whisper 看 model.bin / mlx 看 config.json） */
    downloaded: boolean
  }
  ffmpeg: {
    available: boolean
  }
}

export const getDeployStatus = async (): Promise<DeployStatus> => {
  return await request.get('/deploy_status')
}

export interface AppSettings {
  /** 笔记生成成功后，自动删除本次任务用到的视频/音频文件 */
  auto_delete_media: boolean
  /** 可选：视频/音频的下载保存目录（容器内绝对路径）；空字符串表示用默认目录 */
  download_dir: string
}

export const getAppSettings = async (): Promise<AppSettings> => {
  return await request.get('/app_settings')
}

export const updateAppSettings = async (data: Partial<AppSettings>): Promise<AppSettings> => {
  return await request.post('/app_settings', data)
}

export interface DirEntry {
  name: string
  path: string
}

export interface DirListing {
  /** 当前所在目录 */
  path: string
  /** 上级目录；已经是根目录时为 null */
  parent: string | null
  /** 子目录列表 */
  dirs: DirEntry[]
  /** 当前目录是否可写 */
  writable: boolean
  /** 快捷跳转入口 */
  quick: string[]
}

/**
 * 列出目录下的子目录。
 * 浏览器拿不到用户本机路径，所以"选择文件夹"只能在后端可见的目录树里点选。
 */
export const listDirs = async (path: string): Promise<DirListing> => {
  return await request.get('/fs/list_dirs', { params: { path } })
}

