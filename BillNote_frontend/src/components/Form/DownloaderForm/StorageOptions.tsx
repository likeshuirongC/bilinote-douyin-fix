import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Switch } from '@/components/ui/switch.tsx'
import { Input } from '@/components/ui/input.tsx'
import { Button } from '@/components/ui/button.tsx'
import { getAppSettings, updateAppSettings } from '@/services/system.ts'

/**
 * 下载相关的存储选项：
 *  1) 可选：视频/音频的下载保存目录
 *  2) 笔记生成成功后自动删除视频/音频
 */
const StorageOptions = () => {
  const [loading, setLoading] = useState(true)

  /* ---- 自动删除视频 ---- */
  const [autoDelete, setAutoDelete] = useState(false)

  /* ---- 自定义下载目录 ---- */
  const [downloadDir, setDownloadDir] = useState('')
  const [savedDir, setSavedDir] = useState('')   // 已保存的值，用来判断有没有未保存改动
  const [savingDir, setSavingDir] = useState(false)

  useEffect(() => {
    getAppSettings()
      .then((s) => {
        setAutoDelete(!!s?.auto_delete_media)
        const dir = s?.download_dir || ''
        setDownloadDir(dir)
        setSavedDir(dir)
      })
      .catch(() => { /* 读取失败保持默认，不打扰用户 */ })
      .finally(() => setLoading(false))
  }, [])

  const handleChange = async (next: boolean) => {
    const prev = autoDelete
    setAutoDelete(next)
    try {
      await updateAppSettings({ auto_delete_media: next })
      toast.success(next ? '已开启：生成笔记后自动删除视频' : '已关闭自动删除')
    }
    catch (e: any) {
      setAutoDelete(prev)
      toast.error('保存失败：' + (e?.message || e))
    }
  }

  const handleSaveDir = async () => {
    const next = downloadDir.trim()
    setSavingDir(true)
    try {
      const s = await updateAppSettings({ download_dir: next })
      const saved = s?.download_dir || ''
      setDownloadDir(saved)
      setSavedDir(saved)
      toast.success(saved ? '下载目录已保存' : '已恢复默认下载目录')
    }
    catch (e: any) {
      toast.error('保存失败：' + (e?.message || e))
    }
    finally {
      setSavingDir(false)
    }
  }

  const dirty = downloadDir.trim() !== savedDir

  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-light">存储</div>

      <div className="rounded-lg border border-neutral-200 p-3">
        <div className="text-sm text-gray-800">视频下载保存目录</div>
        <div className="mt-1 text-xs leading-relaxed text-gray-500">
          留空使用默认目录。填写后，下载的视频与音频都会存到这里（填<b>容器内绝对路径</b>）。
          <br />
          当前部署把项目的 <code>backend/</code> 目录映射到了容器 <code>/app</code>，所以填
          <code className="mx-1">/app/downloads</code>
          就相当于存到你电脑的
          <code className="mx-1">BiliNote\backend\downloads</code>。
          若想放到别处，可在项目根目录 <code>.env</code> 里加一行
          <code className="mx-1">DOWNLOAD_HOST_DIR=F:\你的文件夹</code>
          再重启容器，然后这里仍填 <code>/app/downloads</code>。
        </div>
        <div className="mt-2 flex items-center gap-2">
          <Input
            value={downloadDir}
            onChange={e => setDownloadDir(e.target.value)}
            placeholder="例如 /app/downloads（留空用默认）"
            disabled={loading || savingDir}
            className="h-9 text-sm"
          />
          <Button
            size="sm"
            onClick={handleSaveDir}
            disabled={loading || savingDir || !dirty}
          >
            {savingDir ? '保存中…' : '保存'}
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm text-gray-800">笔记生成后自动删除视频</div>
            <div className="mt-1 text-xs leading-relaxed text-gray-500">
              任务成功生成笔记后，自动删除本次下载/上传的视频与音频文件，只保留笔记、转写记录和封面，
              用于节省磁盘空间。默认关闭。
            </div>
          </div>
          <Switch checked={autoDelete} onCheckedChange={handleChange} disabled={loading} />
        </div>
      </div>
    </div>
  )
}

export default StorageOptions
