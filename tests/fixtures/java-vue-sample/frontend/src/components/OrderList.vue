<template>
  <div class="order-list">
    <div v-for="order in orders" :key="order.id" class="order-item">
      <span>{{ order.id }}</span>
      <span>{{ order.status }}</span>
      <button @click="approve(order.id)" v-if="order.status === 'PENDING'">审批</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'OrderList',
  data() {
    return { orders: [] }
  },
  methods: {
    async approve(id) {
      await this.$api.put(`/api/orders/${id}/approve`)
      this.fetchOrders()
    },
    async fetchOrders() {
      this.orders = await this.$api.get('/api/orders')
    }
  },
  mounted() { this.fetchOrders() }
}
</script>
