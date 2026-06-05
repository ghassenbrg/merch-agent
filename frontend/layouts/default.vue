<script setup lang="ts">
import {
  Activity,
  FileText,
  LayoutDashboard,
  Settings,
  ShieldCheck,
} from '@lucide/vue'

const route = useRoute()

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, count: '2' },
  { to: '/drafts', label: 'Drafts', icon: FileText },
  { to: '/runs', label: 'Runs', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const isActive = (to: string) => {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">M</span>
        <span>
          <strong>Merch Agent</strong>
          <small>Local draft ops</small>
        </span>
      </div>
      <nav class="nav-list">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
          :to="item.to"
          :aria-current="isActive(item.to) ? 'page' : undefined"
        >
          <span class="nav-item-label">
            <component :is="item.icon" :size="17" :stroke-width="2.1" />
            {{ item.label }}
          </span>
          <span v-if="item.count" class="nav-count">{{ item.count }}</span>
        </NuxtLink>
      </nav>
      <div class="sidebar-note">
        <ShieldCheck :size="18" :stroke-width="2.1" />
        <span>Autopilot never touches Amazon. Draft assist is one package at a time.</span>
      </div>
    </aside>
    <main class="main">
      <slot />
    </main>
  </div>
</template>
