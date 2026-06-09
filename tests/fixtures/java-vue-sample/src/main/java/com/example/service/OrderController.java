package com.example.service;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @PostMapping
    public Order create(@RequestBody CreateOrderRequest req) {
        return orderService.createOrder(req.getUserId(), req.getProductId(), req.getQuantity());
    }

    @GetMapping("/{id}")
    public Order get(@PathVariable String id) {
        return orderService.getOrder(id);
    }

    @PutMapping("/{id}/approve")
    public Order approve(@PathVariable String id) {
        return orderService.approveOrder(id);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable String id) {
        orderService.deleteOrder(id);
    }
}
