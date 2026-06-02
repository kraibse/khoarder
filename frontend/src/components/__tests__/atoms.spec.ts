import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import FilterChip from '@/components/atoms/FilterChip.vue'
import AppIcon from '@/components/atoms/AppIcon.vue'

describe('FilterChip', () => {
  it('renders label', () => {
    const wrapper = mount(FilterChip, {
      props: { label: 'Articles', active: false },
    })
    expect(wrapper.text()).toContain('Articles')
  })

  it('emits click on click', async () => {
    const wrapper = mount(FilterChip, {
      props: { label: 'Notes', active: false },
    })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('has active styling when active', () => {
    const wrapper = mount(FilterChip, {
      props: { label: 'All', active: true },
    })
    expect(wrapper.classes()).toContain('bg-accent-bg')
    expect(wrapper.classes()).toContain('text-accent')
  })
})

describe('AppIcon', () => {
  it('renders an svg', () => {
    const wrapper = mount(AppIcon, {
      props: { name: 'search', size: 16 },
    })
    expect(wrapper.find('svg').exists()).toBe(true)
  })
})
