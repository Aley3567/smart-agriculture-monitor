import { ref } from 'vue'
import api from '../utils/api'

export function usePaginatedFetch(url) {
  const dateRange = ref([])
  const tableData = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(50)
  const loading = ref(false)

  async function fetch() {
    if (!dateRange.value || dateRange.value.length < 2) return null
    loading.value = true
    try {
      const [start, end] = dateRange.value
      const res = await api.get(url, {
        params: {
          start: start.toISOString(),
          end: end.toISOString(),
          page: currentPage.value,
          page_size: pageSize.value,
        },
      })
      tableData.value = res.data.items
      total.value = res.data.total
      return res.data
    } catch {
      tableData.value = []
      total.value = 0
      return null
    } finally {
      loading.value = false
    }
  }

  function handlePageChange(page) {
    currentPage.value = page
    fetch()
  }

  return { dateRange, tableData, total, currentPage, pageSize, loading, fetch, handlePageChange }
}
