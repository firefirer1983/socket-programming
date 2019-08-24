import asyncio
import collections


class QueueNode:
    
    def __init__(self, name, head=None):
        self._name = name
        if head:
            self._head = head
        else:
            self._head = self
        self._prev = self
        self._next = self
    
    @property
    def next(self):
        return self._next
    
    @next.setter
    def next(self, value):
        self._next = value
    
    @property
    def prev(self):
        return self._prev
    
    @prev.setter
    def prev(self, value):
        self._prev = value
    
    @property
    def name(self):
        return self._name
    
    def __str__(self):
        return self._name
    
    def __iter__(self):
        curr_ = self
        while True:
            yield curr_
            curr_ = curr_.next
            if curr_ == self:
                break
    
    def insert_tail(self, node):
        self._head.prev.next = node
        node.prev = self._head.prev
        self._head.prev = node
        node.next = self._head


def insert_tail(head, node):
    head.prev.next = node
    node.prev = head.prev
    head.prev = node
    node.next = head


def main():
    qh = QueueNode('head')
    first = QueueNode('first', qh)
    second = QueueNode('second', qh)
    third = QueueNode('third', qh)
    qh.insert_tail(first)
    first.insert_tail(second)
    first.insert_tail(third)
    for n in second:
        print(':', n)


def gen():
    yield from gen_inner()
    
    
def gen_inner():
    return [1, 2, 3, 4, 5]


def test_yield_from():
    for i in gen():
        print(i)


if __name__ == '__main__':
    test_yield_from()
