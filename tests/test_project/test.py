from clade.extensions.alternatives import Alternatives

a = Alternatives("clade")

l = set()

for _ in range(100000000):
    l.add(a.get_canonical_path2("/tmp"))

print(len(l))
