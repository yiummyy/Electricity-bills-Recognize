import { ref, readonly } from 'vue'

export interface TaskOptions {
  priority?: number // Higher executes first
  timeout?: number // ms
  retries?: number
  id?: string
}

export interface TaskMetrics {
  id: string
  queuedAt: number
  startedAt?: number
  finishedAt?: number
  duration?: number
  retries: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  error?: Error
}

type TaskFn<T> = () => Promise<T>

interface QueueItem<T> {
  fn: TaskFn<T>
  options: Required<TaskOptions>
  resolve: (value: T | PromiseLike<T>) => void
  reject: (reason?: any) => void
  metrics: TaskMetrics
}

export class ConcurrencyController {
  private maxParallel = ref(1)
  private activeCount = ref(0)
  private queue: QueueItem<any>[] = []
  private _metrics = ref<TaskMetrics[]>([])
  
  // Singleton instance
  private static instance: ConcurrencyController

  public static getInstance(): ConcurrencyController {
    if (!ConcurrencyController.instance) {
      ConcurrencyController.instance = new ConcurrencyController()
    }
    return ConcurrencyController.instance
  }

  constructor(initialMax = 1) {
    this.maxParallel.value = initialMax
  }

  public setMaxParallel(n: number) {
    const val = Math.max(1, Math.min(3, Math.floor(n)))
    this.maxParallel.value = val
    this.processQueue()
  }

  public getMaxParallel() {
    return readonly(this.maxParallel)
  }

  public getActiveCount() {
    return readonly(this.activeCount)
  }

  public getQueueLength() {
    return this.queue.length
  }

  public getMetrics() {
    return readonly(this._metrics)
  }

  public submit<T>(fn: TaskFn<T>, options: TaskOptions = {}): Promise<T> {
    const opts: Required<TaskOptions> = {
      priority: options.priority ?? 0,
      timeout: options.timeout ?? 30000,
      retries: options.retries ?? 2,
      id: options.id ?? `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    }

    const metrics: TaskMetrics = {
      id: opts.id,
      queuedAt: Date.now(),
      retries: 0,
      status: 'pending'
    }
    this._metrics.value.push(metrics)

    return new Promise<T>((resolve, reject) => {
      this.queue.push({
        fn,
        options: opts,
        resolve,
        reject,
        metrics
      })
      // Sort by priority (descending)
      this.queue.sort((a, b) => b.options.priority - a.options.priority)
      this.processQueue()
    })
  }

  private async processQueue() {
    if (this.activeCount.value >= this.maxParallel.value || this.queue.length === 0) {
      return
    }

    const item = this.queue.shift()
    if (!item) return

    this.activeCount.value++
    item.metrics.status = 'running'
    item.metrics.startedAt = Date.now()

    this.executeTask(item)
  }

  private async executeTask<T>(item: QueueItem<T>) {
    const { fn, options, resolve, reject, metrics } = item
    
    // Timeout Race
    let timeoutId: any
    const timeoutPromise = new Promise<never>((_, rej) => {
      timeoutId = setTimeout(() => {
        rej(new Error(`Task timed out after ${options.timeout}ms`))
      }, options.timeout)
    })

    try {
      const result = await Promise.race([fn(), timeoutPromise])
      clearTimeout(timeoutId)
      
      metrics.finishedAt = Date.now()
      metrics.duration = metrics.finishedAt - (metrics.startedAt || 0)
      metrics.status = 'completed'
      resolve(result)
    } catch (error: any) {
      clearTimeout(timeoutId)
      
      if (metrics.retries < options.retries) {
        metrics.retries++
        console.warn(`Task ${metrics.id} failed, retrying (${metrics.retries}/${options.retries})...`, error)
        
        // Re-queue with high priority to retry soon
        this.queue.unshift(item)
        this.activeCount.value-- // Release slot temporarily
        this.processQueue() // Trigger loop
        return
      }

      metrics.finishedAt = Date.now()
      metrics.duration = metrics.finishedAt - (metrics.startedAt || 0)
      metrics.status = 'failed'
      metrics.error = error
      reject(error)
    } finally {
      // Only decrement if we didn't re-queue
      if (metrics.status === 'completed' || metrics.status === 'failed') {
        this.activeCount.value--
        this.processQueue()
      }
    }
  }
}

export const scheduler = ConcurrencyController.getInstance()
