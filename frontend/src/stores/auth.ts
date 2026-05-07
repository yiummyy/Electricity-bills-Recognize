import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const username = ref(localStorage.getItem('auth_username') || '')
  const role = ref(localStorage.getItem('auth_role') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  function saveAuth(t: string, u: string, r: string) {
    token.value = t
    username.value = u
    role.value = r
    localStorage.setItem('auth_token', t)
    localStorage.setItem('auth_username', u)
    localStorage.setItem('auth_role', r)
    // Set axios default header so all subsequent requests include the token
    api.defaults.headers.common['Authorization'] = `Bearer ${t}`
  }

  function clearAuth() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_username')
    localStorage.removeItem('auth_role')
    delete api.defaults.headers.common['Authorization']
  }

  async function login(user: string, password: string) {
    const formData = new FormData()
    formData.append('username', user)
    formData.append('password', password)
    const resp = await api.post('/login/access-token', formData)
    saveAuth(resp.data.access_token, resp.data.username, resp.data.role)
    return resp.data
  }

  async function register(user: string, password: string) {
    const resp = await api.post('/register', { username: user, password: password })
    saveAuth(resp.data.access_token, resp.data.username, resp.data.role)
    return resp.data
  }

  function logout() {
    clearAuth()
  }

  // Restore auth header on init if token exists
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  return { token, username, role, isLoggedIn, isAdmin, login, register, logout }
})
