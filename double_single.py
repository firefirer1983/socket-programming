ary = [56, 78, 76, 3, 5, 76, 5, 56]


def xor_sum(mm):
    ret = mm.pop()
    while mm:
        m = mm.pop()
        ret ^= m
    return ret


print(ary)
xsum = xor_sum(ary.copy())
print(xsum)
a1 = [a ^ xsum for a in ary]
print(a1)
d = [a1[i] + a for i, a in enumerate(ary)]
print(d)
