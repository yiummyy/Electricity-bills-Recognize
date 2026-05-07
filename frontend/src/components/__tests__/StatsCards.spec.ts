import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatsCards from '../StatsCards.vue'

describe('StatsCards', () => {
  it('renders properly with empty data', () => {
    const wrapper = mount(StatsCards, { props: { data: [] } })
    expect(wrapper.text()).toContain('累计电费支出')
    expect(wrapper.text()).toContain('¥ 0')
  })

  it('calculates totals correctly', () => {
    const mockData = [
      { '总电费(元)': '100', '总电量(kWh)': '50', '电费年月': '2024-01' },
      { '总电费(元)': '200', '总电量(kWh)': '100', '电费年月': '2024-02' }
    ]
    const wrapper = mount(StatsCards, { props: { data: mockData as any } })
    
    // Total Cost: 300
    // Total Usage: 150
    // Avg Price: 300/150 = 2.0000
    
    expect(wrapper.text()).toContain('¥ 300.00')
    expect(wrapper.text()).toContain('150.00 kWh')
    expect(wrapper.text()).toContain('¥ 2.0000 /kWh')
  })
})
