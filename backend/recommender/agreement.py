"""Inter-annotator agreement and freeze conditions for the gold sets (Measured Matching C3, #159).

Computed per split, on the two independent annotations, before adjudication. The freeze
conditions are the plan's (revision 3 R4, revision 4 §C2):

| Labels              | Freeze when                                                              |
|---------------------|--------------------------------------------------------------------------|
| Sufficiency         | 3-class raw agreement >= 0.75, 3-class kappa >= 0.60, and min(kappa with |
|                     | borderline as sufficient, kappa with borderline as insufficient) >= 0.60 |
| Career grades       | quadratic-weighted kappa >= 0.60 and mean grade-3 Jaccard >= 0.70        |
| Mapping class       | Cohen's kappa >= 0.60                                                    |
| Mapping acceptable  | mean Jaccard >= 0.70, on items both annotators call unambiguous          |
| Concept pairs       | reported only                                                            |

Jaccard of two empty sets is 1 (both annotators agree there is nothing); of one empty and
one non-empty set, 0.
"""

from collections import Counter

SUFFICIENCY = ('sufficient', 'borderline', 'insufficient')
MAPPING_CLASSES = ('unambiguous', 'ambiguous', 'no_concept')
KAPPA_MIN = 0.60
RAW_MIN_3CLASS = 0.75
JACCARD_MIN = 0.70


def cohen_kappa(a, b):
    """Cohen's kappa for two equal-length label sequences."""
    if len(a) != len(b) or not a:
        raise ValueError('need two non-empty sequences of the same length')
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def weighted_kappa(a, b, levels):
    """Quadratic-weighted kappa for ordinal labels taking values in `levels` (ordered)."""
    if len(a) != len(b) or not a:
        raise ValueError('need two non-empty sequences of the same length')
    index = {v: i for i, v in enumerate(levels)}
    k, n = len(levels), len(a)
    weight = lambda i, j: (i - j) ** 2 / (k - 1) ** 2
    ca, cb = Counter(index[x] for x in a), Counter(index[y] for y in b)
    observed = sum(weight(index[x], index[y]) for x, y in zip(a, b)) / n
    expected = sum(ca[i] * cb[j] * weight(i, j) for i in range(k) for j in range(k)) / (n * n)
    if expected == 0:
        return 1.0 if observed == 0 else 0.0
    return 1 - observed / expected


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def raw_agreement(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a)


def sufficiency_agreement(a, b):
    """Revision 4 §C2 report for one split: `a`, `b` are the two annotators' labels per profile."""
    confusion = {x: {y: 0 for y in SUFFICIENCY} for x in SUFFICIENCY}
    for x, y in zip(a, b):
        confusion[x][y] += 1
    resolve = lambda labels, to: [to if v == 'borderline' else v for v in labels]
    as_s, as_i = (resolve(a, 'sufficient'), resolve(b, 'sufficient')), (resolve(a, 'insufficient'), resolve(b, 'insufficient'))
    restricted = [(x, y) for x, y in zip(a, b) if x != 'borderline' and y != 'borderline']
    excluded = Counter(tuple(sorted((x[0].upper(), y[0].upper()))) for x, y in zip(a, b)
                       if 'borderline' in (x, y))
    report = {
        'n': len(a),
        'confusion (rows A, columns B)': confusion,
        '3-class raw agreement': raw_agreement(a, b),
        '3-class kappa': cohen_kappa(a, b),
        'borderline rate A': a.count('borderline') / len(a),
        'borderline rate B': b.count('borderline') / len(b),
        'borderline rate either': sum('borderline' in p for p in zip(a, b)) / len(a),
        'B->S raw agreement': raw_agreement(*as_s), 'B->S kappa': cohen_kappa(*as_s),
        'B->I raw agreement': raw_agreement(*as_i), 'B->I kappa': cohen_kappa(*as_i),
        'restricted n': len(restricted),
        'restricted excluded pairs': {'-'.join(k): v for k, v in sorted(excluded.items())},
        'restricted kappa': cohen_kappa(*zip(*restricted)) if restricted else None,
    }
    report['freeze'] = (report['3-class raw agreement'] >= RAW_MIN_3CLASS and report['3-class kappa'] >= KAPPA_MIN
                        and min(report['B->S kappa'], report['B->I kappa']) >= KAPPA_MIN)
    return report


def grade_agreement(a, b, careers):
    """Career grades for one split. `a`, `b`: per profile, {career code: grade 1-3} (0 implicit)."""
    ga = [pa.get(c, 0) for pa in a for c in careers]
    gb = [pb.get(c, 0) for pb in b for c in careers]
    threes = [(frozenset(c for c, g in pa.items() if g == 3), frozenset(c for c, g in pb.items() if g == 3))
              for pa, pb in zip(a, b)]
    js = [jaccard(x, y) for x, y in threes]
    nonempty = [j for (x, y), j in zip(threes, js) if x or y]
    report = {
        'profiles': len(a),
        'pairs': len(ga),
        'quadratic weighted kappa': weighted_kappa(ga, gb, (0, 1, 2, 3)),
        'exact grade agreement': raw_agreement(ga, gb),
        'grade-3 Jaccard (mean)': sum(js) / len(js),
        'profiles with both grade-3 sets empty': len(js) - len(nonempty),
        'grade-3 Jaccard (mean, excluding both empty)': sum(nonempty) / len(nonempty) if nonempty else None,
    }
    report['freeze'] = report['quadratic weighted kappa'] >= KAPPA_MIN and report['grade-3 Jaccard (mean)'] >= JACCARD_MIN
    return report


def mapping_agreement(a, b):
    """Mapping labels for one split. `a`, `b`: per item, {'label', 'acceptable', 'preferred'}."""
    la, lb = [x['label'] for x in a], [y['label'] for y in b]
    both = [(x, y) for x, y in zip(a, b) if x['label'] == y['label'] == 'unambiguous']
    js = [jaccard(x['acceptable'], y['acceptable']) for x, y in both]
    report = {
        'n': len(a),
        'class raw agreement': raw_agreement(la, lb),
        'class kappa': cohen_kappa(la, lb),
        'both unambiguous': len(both),
        'acceptable Jaccard (mean, both unambiguous)': sum(js) / len(js) if js else None,
        'preferred exact agreement (both unambiguous)':
            sum(x.get('preferred') == y.get('preferred') for x, y in both) / len(both) if both else None,
    }
    report['freeze class'] = report['class kappa'] >= KAPPA_MIN
    report['freeze acceptable'] = js != [] and report['acceptable Jaccard (mean, both unambiguous)'] >= JACCARD_MIN
    return report
