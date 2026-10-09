import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Switch } from '@/components/ui/switch.tsx'
import { getAppSettings, updateAppSettings } from '@/services/system.ts'

/**
 * 下载相关的存储选项。
 * 目前只有一项：笔记生成成功后自动删除本次任务的视频/音频文件。
 */
const StorageOptions = () => {
  const [autoDelete, setAutoDelete] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAppSettings()
      .then(s => setAutoDelete(!!s?.auto_delete_media))
      .catch(() => { /* 设置项读取失败时保持默认关闭，不打扰用户 */ })
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

  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-light">存储</div>
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
