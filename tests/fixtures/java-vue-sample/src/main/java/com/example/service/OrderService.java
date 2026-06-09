package com.example.service;

import org.springframework.transaction.annotation.Transactional;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.security.access.prepost.PreAuthorize;
import com.example.model.OrderStatus;

public class OrderService {

    @Transactional
    @PreAuthorize("hasRole('ORDER_MANAGER')")
    public Order createOrder(String userId, String productId, int quantity) {
        Order order = new Order();
        order.setStatus(OrderStatus.PENDING);
        // optimistic lock via @Version field
        return orderRepository.save(order);
    }

    @Cacheable("orders")
    public Order getOrder(String orderId) {
        return orderRepository.findById(orderId);
    }

    @Transactional
    public Order approveOrder(String orderId) {
        Order order = orderRepository.findById(orderId);
        order.setStatus(OrderStatus.APPROVED);
        return orderRepository.save(order);
    }

    public void deleteOrder(String orderId) {
        Order order = orderRepository.findById(orderId);
        order.setDeleted(true); // soft delete
        orderRepository.save(order);
    }
}
