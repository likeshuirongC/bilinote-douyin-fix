import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx'
import { Button } from '@/components/ui/button.tsx'
import { listDirs, type DirListing } from '@/services/system.ts'

interface DirPickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** 选中某个目录后回调 */
  onPick: (path: string) => void
  /** 打开时定位到的目录 */
  initial?: string
}

/**
 * 服务端目录选择器。
 * 浏览器出于安全无法给出本机路径，所以这里让后端列出目录树，用户逐层点选。
 */
const DirPickerDialog = ({ open, onOpenChange, onPick, initial }: DirPickerDialogProps) => {
  const [listing, setListing] = useState<DirListing | null>(null)
  const [loading, setLoading] = useState(false)

  const load = async (path: string) => {
    setLoading(true)
    try {
      const data = await listDirs(path)
      setListing(data)
    }
    catch (e: any) {
      toast.error('读取目录失败：' + (e?.message || e))
    }
    finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open)
      load(initial || '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const cur = listing?.path || ''

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>选择下载保存目录</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="shrink-0 text-xs text-gray-500">当前位置</span>
            <code className="min-w-0 flex-1 truncate rounded bg-neutral-100 px-2 py-1 text-xs">
              {cur || '…'}
            </code>
            {listing?.writable === false && (
              <span className="shrink-0 text-xs text-amber-600">不可写</span>
            )}
          </div>

          {!!listing?.quick?.length && (
            <div className="flex flex-wrap gap-1">
              {listing.quick.map(q => (
                <button
                  key={q}
                  type="button"
                  onClick={() => load(q)}
                  className="rounded border border-neutral-200 px-2 py-0.5 text-xs text-gray-600 hover:bg-neutral-50"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          <div className="h-64 overflow-y-auto rounded-lg border border-neutral-200">
            {loading && <div className="p-3 text-xs text-gray-400">读取中…</div>}

            {!loading && listing?.parent && (
              <button
                type="button"
                onClick={() => load(listing.parent as string)}
                className="flex w-full items-center gap-2 border-b border-neutral-100 px-3 py-2 text-left text-sm hover:bg-neutral-50"
              >
                <span className="text-gray-400">↰</span>
                <span>上级目录</span>
              </button>
            )}

            {!loading && !listing?.dirs?.length && (
              <div className="p-3 text-xs text-gray-400">（没有子文件夹）</div>
            )}

            {!loading && listing?.dirs?.map(d => (
              <button
                key={d.path}
                type="button"
                onClick={() => load(d.path)}
                className="flex w-full items-center gap-2 border-b border-neutral-100 px-3 py-2 text-left text-sm hover:bg-neutral-50"
              >
                <span className="text-amber-500">📁</span>
                <span className="min-w-0 flex-1 truncate">{d.name}</span>
                <span className="shrink-0 text-xs text-gray-300">进入 ›</span>
              </button>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button
            onClick={() => {
              if (!cur)
                return
              onPick(cur)
              onOpenChange(false)
            }}
            disabled={!cur || loading || listing?.writable === false}
          >
            选择此文件夹
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default DirPickerDialog
