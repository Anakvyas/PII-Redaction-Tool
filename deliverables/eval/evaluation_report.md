# Evaluation Report

## Overall

| Label | TP | FP | FN | Precision | Recall | F1 | Entity Accuracy | Support |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| overall | 23 | 107 | 16 | 0.1769 | 0.5897 | 0.2722 | 0.1575 | 39 |

## Classification Report

| Label | TP | FP | FN | Precision | Recall | F1 | Entity Accuracy | Support |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| address | 4 | 43 | 10 | 0.0851 | 0.2857 | 0.1311 | 0.0702 | 14 |
| company | 4 | 57 | 0 | 0.0656 | 1.0000 | 0.1231 | 0.0656 | 4 |
| email | 5 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5 |
| person | 7 | 6 | 6 | 0.5385 | 0.5385 | 0.5385 | 0.3684 | 13 |
| phone | 3 | 1 | 0 | 0.7500 | 1.0000 | 0.8571 | 0.7500 | 3 |

## Confusion Matrix

| Actual \ Predicted | __none__ | address | company | email | person | phone |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| __none__ | 0 | 43 | 47 | 0 | 4 | 1 |
| address | 0 | 4 | 8 | 0 | 2 | 0 |
| company | 0 | 0 | 4 | 0 | 0 | 0 |
| email | 0 | 0 | 0 | 5 | 0 | 0 |
| person | 4 | 0 | 2 | 0 | 7 | 0 |
| phone | 0 | 0 | 0 | 0 | 0 | 3 |

## Formulas

- **true_positive**: `Predicted entity overlaps an unmatched ground-truth entity with the same type.`
- **false_positive**: `Predicted entity has no overlapping ground truth, or overlaps a different type.`
- **false_negative**: `Ground-truth entity has no overlapping prediction with the same type.`
- **precision**: `TP / (TP + FP)`
- **recall**: `TP / (TP + FN)`
- **f1**: `2 * Precision * Recall / (Precision + Recall)`
- **entity_accuracy**: `TP / (TP + FP + FN)`
