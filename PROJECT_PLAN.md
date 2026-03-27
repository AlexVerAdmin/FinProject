# HauptProject — Plan

## Легенда
- `[ ]` — не начато
- `[~]` — в процессе
- `[x]` — выполнено

---

## Концепция
Аналитик данных в онлайн-школе программирования X. Данные CRM за июль 2023 — июнь 2024.
Цель: очистка, анализ данных, юнит-экономика, рекомендации по росту бизнеса.

---

## Структура проекта

```
HauptProject/
├── Sources/                      # исходные данные (не изменять!)
│   ├── Contacts (Done).xlsx
│   ├── Spend (Done).xlsx
│   ├── Deals (Done).xlsx
│   ├── Calls (Done).xlsx
│   └── Python for DA_LfS_Project.pdf   # описание проекта
├── notebooks/
│   ├── help_130625_dam.py        # утилиты: descr_df(), hist_box(), iqr_outliers()
│   ├── 01_cleaning_contacts.ipynb
│   ├── 02_cleaning_spend.ipynb
│   ├── 03_cleaning_deals.ipynb
│   ├── 04_cleaning_calls.ipynb
│   ├── 05_data_merging.ipynb
│   ├── 06_descriptive_stats.ipynb    # ← следующий
│   ├── 07_analysis.ipynb
│   └── 08_unit_economics.ipynb
├── data/cleaned/                 # pkl-файлы (генерируются ноутбуками)
├── report/                       # PPTX-презентация
├── requirements.txt
└── PROJECT_PLAN.md
```

---

## Датасеты и связи

| Файл | Строк сырых | Столбец-ключ |
|------|-------------|--------------|
| Contacts (Done).xlsx | 18 548 | `Id` |
| Spend (Done).xlsx | ~20 779 | `Date + Source + Campaign` |
| Deals (Done).xlsx | ~21 595 | `Id`, `Contact Name → Contacts.Id` |
| Calls (Done).xlsx | ~95 874 | `CONTACTID → Contacts.Id` |

Связи: `Deals.Contact Name ↔ Contacts.Id ↔ Calls.CONTACTID`

---

## Сохранённые PKL-файлы (актуальный статус)

| Файл | Размер | Описание |
|------|--------|----------|
| `contacts_clean.pkl` | (18 548, 4) | Id, Contact Owner Name, Created Time, Modified Time |
| `spend_clean.pkl` | (19 862, 8) | Date, Source, Campaign, Spend, Clicks, Impressions, AdGroup, Ad |
| `deals_clean.pkl` | (21 591, 24) | все поля сделок, Contact Name → Int64 (прецизионный фикс) |
| `calls_clean.pkl` | (95 874, 9) | CONTACTID → Int64, Is Successful, Call Duration |
| `master_clean.pkl` | (18 548, 28) | 1 строка = 1 контакт, агрегированные сделки + звонки |
| `cohort_economics.pkl` | (153, 13) | 1 строка = Source + Cohort, CAC / ROAS / Conv_Rate |

---

## ЭТАП 1 — ОЧИСТКА ДАННЫХ `[x]`

### `[x]` 01_cleaning_contacts.ipynb → `contacts_clean.pkl`
- [x] Дедупликация по `Id`
- [x] `Created Time`, `Modified Time` → `datetime64[ns]`
- [x] `Contact Owner Name` → category
- [x] Проверка и документирование пропусков
- [x] Сохранение → `contacts_clean.pkl`

### `[x]` 02_cleaning_spend.ipynb → `spend_clean.pkl`
- [x] Дедупликация
- [x] `Date` → `datetime64[ns]`
- [x] `Spend`, `Impressions`, `Clicks` → float (очистка символов, отрицательных значений)
- [x] Пропуски: `Campaign`, `AdGroup`, `Ad` → `'Unknown'`
- [x] Анализ распределения по `Source` и `Campaign`
- [x] Сохранение → `spend_clean.pkl`

### `[x]` 03_cleaning_deals.ipynb → `deals_clean.pkl`
- [x] Дедупликация (полные дубли удалены; `Id`-дубли — история воронки, сохранены)
- [x] `Created Time`, `Closing Date` → `datetime64[ns]`
- [x] `SLA` → секунды (из `datetime.time`)
- [x] `Initial Amount Paid`, `Offer Total Amount` → float (очистка '€ 3.500,00')
- [x] `Contact Name` → `Int64` через `str_to_nullable_int64()` (фикс потери точности float64)
- [x] `Level of Deutsch` → стандарт CEFR (A0–C2)
- [x] Пропуски категориальных полей → `'Unknown'`
- [x] `Stage Group` — новый столбец: `'Won/Paid'` / `'Lost'` / `'In Progress'`
- [x] Сохранение → `deals_clean.pkl`

### `[x]` 04_cleaning_calls.ipynb → `calls_clean.pkl`
- [x] Дедупликация по `Id`
- [x] `Call Start Time` → `datetime64[ns]`
- [x] `Call Duration (in seconds)` → float
- [x] `CONTACTID` → `Int64` через `str_to_nullable_int64()` (фикс потери точности float64)
- [x] `Is Successful` → bool (на основе `Call Status`)
- [x] Удалены полностью пустые / нерелевантные столбцы
- [x] Сохранение → `calls_clean.pkl`

### `[x]` 05_data_merging.ipynb → `master_clean.pkl`, `cohort_economics.pkl`
- [x] `Cohort` = `contacts.Created Time.dt.to_period('M')` → добавлен к contacts
- [x] `Cohort` → deals через `Contact Name → contacts.Id` map (99.7% matched)
- [x] `Cohort` → spend через `Date.dt.to_period('M')`
- [x] `deals_agg` по `Contact Name`: Deals_Count, Deals_Won, Source, Campaign, Revenue, Product...
- [x] `master` = contacts LEFT JOIN deals_agg (97.5% контактов имеют сделку)
- [x] `calls_agg` по `CONTACTID`: Calls_Total, Calls_Successful, Duration...
- [x] `master` += calls_agg (15 214 контактов с звонками)
- [x] `cohort_economics` = master_agg JOIN spend_by_source_cohort → CAC, ROAS, Conv_Rate
- [x] Сохранение → `master_clean.pkl` + `cohort_economics.pkl`

---

## ЭТАП 2 — ОПИСАТЕЛЬНАЯ СТАТИСТИКА `[ ]`

### `[ ]` 06_descriptive_stats.ipynb

**Источник данных:** `master_clean.pkl`, `deals_clean.pkl`, `calls_clean.pkl`, `spend_clean.pkl`

#### 2.1 Числовые поля — сводная статистика
Для каждого числового поля рассчитать: **mean, median, mode, range, std, IQR**, визуализировать гистограммой + box-plot.

| Поле | Датасет | Примечание |
|------|---------|------------|
| `Initial Amount Paid` | deals | только где `Stage Group == 'Won/Paid'` и значение > 0 |
| `Offer Total Amount` | deals | только где значение > 0 |
| `Call Duration (in seconds)` | calls | только успешные звонки |
| `Spend` | spend | по строке (агрегированные значения — в разделе кампаний) |
| `Clicks` | spend | — |
| `Impressions` | spend | — |
| `Calls_Total` | master | per contact |
| `Deals_Count` | master | per contact |
| `Call_Duration_Avg` | master | per contact, только > 0 |

Шаги для каждого поля:
1. `series.describe()` → вывести таблицу
2. `series.mode()[0]` → mода
3. `series.max() - series.min()` → range
4. Построить `hist_box(series, title)` из `help_130625_dam.py`
5. Выявить и задокументировать выбросы через `iqr_outliers(series)`
6. Написать текстовый вывод: что говорят цифры о бизнесе

#### 2.2 Категориальные поля — распределение и конверсия
Для каждого поля: **value_counts + bar-chart**, а там где применимо — **конверсия в Won/Paid**.

| Поле | Датасет | Что считать |
|------|---------|-------------|
| `Stage Group` | deals | value_counts + % Won/Paid |
| `Quality` | deals | value_counts + конверсия в Won/Paid по каждому значению |
| `Source` | deals/master | value_counts + конверсия + средний чек |
| `Product` | deals | value_counts + конверсия + средний чек |
| `Education Type` | deals | value_counts + конверсия |
| `Payment Type` | deals | value_counts + конверсия, только Won/Paid |
| `Level of Deutsch` | deals | value_counts + конверсия |
| `City` | deals | топ-15 городов + конверсия |
| `Course duration` | deals | value_counts + конверсия |
| `Call Type` | calls | value_counts + доля успешных |

Шаги для каждого поля:
1. `value_counts(dropna=False)` → таблица с долями
2. Если поле имеет смысл разбить по `Stage Group` — pivot_table: поле × Stage_Group
3. Построить горизонтальный bar-chart (топ-N категорий)
4. Где применимо: добавить линию конверсии (вторая ось)
5. Написать текстовый вывод

#### 2.3 Сводная таблица ключевых метрик (итог раздела)
- Общее кол-во лидов: `len(master)`
- Конверсия лид → сделка: `master.Has_Deal.mean()`
- Конверсия сделка → Won/Paid: `(deals.Stage_Group == 'Won/Paid').mean()`
- Общая выручка: `master.Total_Revenue.sum()`
- Средний чек Won/Paid: `deals[deals.Stage_Group=='Won/Paid']['Initial Amount Paid'].mean()`
- Общие расходы на рекламу: `spend_clean.Spend.sum()`
- Общее кол-во звонков: `len(calls)`
- % успешных звонков: `calls.Is_Successful.mean()`

---

## ЭТАП 3 — ПОЛНЫЙ АНАЛИЗ ДАННЫХ `[ ]`

### `[ ]` 07_analysis.ipynb

**Источник данных:** `master_clean.pkl`, `deals_clean.pkl`, `calls_clean.pkl`, `spend_clean.pkl`, `cohort_economics.pkl`

#### 3.1 Анализ временных рядов

**3.1.1 Динамика создания лидов и сделок**
1. Агрегировать `contacts.Created Time` по неделям и месяцам → `leads_by_week`
2. Агрегировать `deals.Created Time` по неделям → `deals_by_week`
3. Построить line chart: кол-во новых лидов и сделок на одном графике (двойная ось)
4. Вывод: есть ли сезонность? Пики и провалы — когда и почему?

**3.1.2 Связь звонков с созданием лидов**
1. Агрегировать `calls.Call Start Time` по неделям → `calls_by_week`
2. Построить scatter + correlation между `calls_by_week` и `leads_by_week` (с lag 0, +1, +2 недели)
3. Вывод: звонки опережают или следуют за лидами?

**3.1.3 Длительность цикла сделки**
1. Для сделок с `Stage Group == 'Won/Paid'` и непустым `Closing Date`:
   `cycle_days = (deals.Closing Date - deals.Created Time).dt.days`
2. Для сделок `Lost`: то же самое
3. `describe()` + `hist_box()` для обеих групп
4. Вывод: сколько дней в среднем до оплаты? Насколько отличается от потерянных сделок?

**3.1.4 Распределение дат закрытия**
1. `deals[deals.Stage_Group=='Won/Paid']['Closing Date'].dt.to_period('M').value_counts().sort_index()`
2. Bar chart по месяцам
3. Вывод: в какие месяцы больше всего закрытий?

#### 3.2 Анализ эффективности кампаний

**3.2.1 Сравнение Sources**
1. Сгруппировать `master` по `Source`:
   - `Leads` = count
   - `Deals` = Deals_Count.sum()
   - `Won` = Deals_Won.sum()
   - `Revenue` = Total_Revenue.sum()
2. Присоединить расходы: `spend_clean.groupby('Source')['Spend'].sum()`
3. Рассчитать для каждого Source:
   - `Conv_Rate` = Won / Leads × 100
   - `CAC` = Spend / Leads
   - `CPD` = Spend / Won (cost per won deal)
   - `ROAS` = Revenue / Spend
4. Построить: горизонтальный bar-chart по ROAS + таблица всех метрик
5. Вывод: какой канал наиболее эффективен?

**3.2.2 Сравнение кампаний внутри каждого Source**
1. Сгруппировать `deals` по `Campaign`:
   - Leads, Won/Paid deals, конверсия
2. TOP-10 кампаний по конверсии + TOP-10 по кол-ву лидов
3. Присоединить расходы из `spend_clean` по `Campaign`
4. Рассчитать CPL = Spend / Leads для кампаний с известными расходами
5. Вывод: какие кампании генерируют качественные лиды?

**3.2.3 Качество лидов по Source**
1. Сгруппировать `deals` по `Source` × `Quality`:
   `pivot_table(index='Source', columns='Quality', values='Id', aggfunc='count')`
2. Нормировать по строкам → % каждого качества внутри Source
3. Stacked bar chart
4. Вывод: какой источник даёт больше лидов с высоким Quality?

#### 3.3 Анализ эффективности отдела продаж

**3.3.1 Рейтинг менеджеров (Deal Owner)**
1. Сгруппировать `deals` по `Deal Owner Name`:
   - `Deals_Total` = count
   - `Won` = `(Stage Group == 'Won/Paid').sum()`
   - `Lost` = `(Stage Group == 'Lost').sum()`
   - `Conv_Rate` = Won / Deals_Total × 100
   - `Revenue` = `Initial Amount Paid[Stage Group=='Won/Paid'].sum()`
   - `Avg_Revenue` = Revenue / Won
2. Отсортировать по `Revenue` desc
3. Построить: bar chart топ-15 менеджеров по Revenue + annotate Conv_Rate
4. Вывод: топ-5 менеджеров по выручке и по конверсии

**3.3.2 Влияние SLA на конверсию**
1. Из `deals_clean` взять поле `SLA` (секунды от заявки до первого контакта)
2. Создать бины: `[0–5min, 5–30min, 30min–2h, 2h–24h, >24h]`
3. Для каждого бина: кол-во сделок + конверсия в Won/Paid
4. Line chart: SLA бин → конверсия
5. Вывод: насколько быстрый ответ влияет на конверсию?

**3.3.3 Звонки менеджеров и конверсия**
1. Присоединить к `master` информацию о Contact Owner
2. По каждому менеджеру: среднее кол-во звонков на лида + конверсия
3. Scatter plot: `Calls_Total` vs `Conv_Rate` по менеджерам
4. Вывод: есть ли зависимость между интенсивностью звонков и конверсией?

#### 3.4 Анализ платежей и продуктов

**3.4.1 Payment Type — распределение и влияние на успешность**
1. `deals[deals.Stage_Group=='Won/Paid']['Payment Type'].value_counts()` → таблица + pie chart
2. Сравнить средний `Initial Amount Paid` по `Payment Type`
3. Проверить: есть ли расхождения `Initial Amount Paid > Offer Total Amount` → задокументировать решение по ним (например, обнулить или поменять местами)
4. Вывод: какой тип оплаты преобладает?

**3.4.2 Популярность и успешность продуктов**
1. Сгруппировать `deals` по `Product`:
   - `Leads` = count
   - `Won` = `(Stage Group=='Won/Paid').sum()`
   - `Conv_Rate` = Won / Leads × 100
   - `Avg_Revenue` = среднее `Initial Amount Paid` (Win/Paid)
   - `Total_Revenue` = сумма
2. Отсортировать по `Total_Revenue` desc
3. Построить grouped bar: кол-во лидов vs Won по продукту
4. Вывод: какой продукт приносит больше всего выручки / имеет лучшую конверсию?

**3.4.3 Education Type**
1. `deals.groupby('Education Type')` → аналогичная агрегация как в 3.4.2
2. Bar chart: конверсия по Education Type
3. Cross-tab: `Education Type × Product` → heat-map конверсий
4. Вывод: какой тип обучения конвертируется лучше?

#### 3.5 Географический анализ

**3.5.1 Распределение по городам**
1. `deals.groupby('City')` → топ-20 городов по кол-ву лидов + конверсии
2. Bar chart: топ-20 городов по лидам (annotate конверсию)
3. Вывод: в каких городах больше всего клиентов?

**3.5.2 Влияние Level of Deutsch на конверсию**
1. `deals.groupby('Level of Deutsch')`:
   - Leads, Won, Conv_Rate, Avg_Revenue
2. Bar chart: конверсия по уровню языка
3. Cross-tab: `City (топ-5) × Level of Deutsch` → heat-map конверсий
4. Вывод: влияет ли уровень языка на успешность сделки?

---

## ЭТАП 4 — ЮНИТ-ЭКОНОМИКА И ГИПОТЕЗЫ `[ ]`

### `[ ]` 08_unit_economics.ipynb

**Источник данных:** `master_clean.pkl`, `cohort_economics.pkl`, `deals_clean.pkl`

#### 4.1 Юнит-экономика по продуктам
1. Из `master_clean` сгруппировать по `Product`:
   - `Leads` = count
   - `Won` = Deals_Won.sum()
   - `Revenue` = Total_Revenue.sum()
   - `Conv_Rate` = Won / Leads × 100
2. Присоединить расходы: `spend_clean.groupby('Source')` → через связь Source → Product (или аллоцировать пропорционально лидам)
3. Рассчитать:
   - `CAC` = Spend / Won
   - `Avg_Revenue` = Revenue / Won
   - `Gross_Margin` = Avg_Revenue — CAC (упрощённая маржа)
   - `ROAS` = Revenue / Spend
4. Таблица + bar chart: CAC vs Avg_Revenue по продукту
5. Вывод: какой продукт наиболее прибыльный с учётом затрат?

#### 4.2 Воронка продаж (дерево метрик)
1. Построить воронку:
   ```
   Лиды (contacts) → Has_Deal → Calls_Total > 0 → Deals_Won
   ```
2. Для каждого перехода рассчитать конверсию в %
3. Визуализировать funnel chart (plotly `go.Funnel`)
4. Разбить воронку по `Source` (топ-4 источника)
5. Вывод: где самый большой «провал» в воронке?

#### 4.3 Когортный анализ (из cohort_economics.pkl)
1. Pivot-таблица: `Cohort` × `Source` → значение `CAC`
2. Pivot-таблица: `Cohort` × `Source` → значение `ROAS`
3. Line chart: CAC / ROAS по когортам для топ-3 источников
4. Вывод: есть ли тренд ухудшения / улучшения экономики?

#### 4.4 Точки роста
На основе результатов этапов 3 и 4.1–4.3 сформулировать 3–5 точек роста в формате:
- **Что**: описание проблемы / возможности
- **Где**: метрика и значение из анализа
- **Потенциал**: оценка возможного влияния на Revenue или Conv_Rate

#### 4.5 Формулирование и описание гипотез
Для каждой точки роста (минимум 2):
1. **Гипотеза**: «Если [изменение], то [метрика] вырастет на [X%], потому что [обоснование]»
2. **Метрика**: что измеряем (primary KPI)
3. **Метод проверки**: A/B тест или before/after
4. **Условия теста**:
   - Длительность ≤ 2 недели
   - Размер выборки (расчёт MDE / статистической мощности)
   - Группы: контрольная и тестовая
   - Критерий успеха: порог p-value и минимальный эффект

---

## ФИНАЛЬНЫЕ АРТЕФАКТЫ `[ ]`

- [ ] Все ноутбуки с выводами и визуализациями
- [ ] `report/presentation.pptx` — презентация с ключевыми выводами
- [ ] Дашборд (Plotly / отдельный файл) — интерактивная визуализация ключевых метрик

---

## ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ (ревью после выполнения)

### 🔴 Критические (влияют на оценку)

1. **H1 длительность 95 недель** — прямое нарушение требования задания «тест не должен занимать больше 2 недель».
   - Причина: MDE +20% при baseline 5.2% требует огромной выборки (7 827 сделок/группу), а SLA >2ч поступает только 165 сделок/нед.
   - Решение: снизить MDE до +40–50% (с 5.2% до ~7.3–7.8%) или заменить метрику на «время до первого звонка» (в днях) вместо бинарной конверсии.

2. **H2 длительность 12 недель** — также нарушает требование ≤ 2 недели.
   - Причина: Morning-лидов приходит ~56 в неделю при MDE +30%.
   - Решение: поднять MDE до +50–60% или измерять промежуточную метрику (доля Evening-лидов) с более коротким горизонтом.

3. **Раздел 3.3.3 отсутствует в 07_analysis.ipynb** — анализ «звонки менеджеров vs конверсия» (scatter Calls_Total vs Conv_Rate по менеджерам) не реализован.
   - Затрагивает критерий «Анализ данных» в таблице оценки.

4. **Точка роста 3 — Revenue потенциал €172M математически завышен в ~50x.**
   - Причина: формула `known_conv_% × unk_leads × 0.5 × avg_revenue` — `known_conv` взята не как доля [0,1], а как процент (19.6); итог = 19.6 × 15152 × 0.5 × 1168 ≈ €173M.
   - Решение: разделить `known_conv` на 100. Корректное значение ~€1.7M.

### 🟡 Важные (снижают качество)

5. **Точка роста 4 (Google Ads CAC) — данные конфликтуют с графиком.**
   - Код вычисляет CAC из `cohort_economics` как `spend/leads` per source (€17 → €17, дельта -2%), тогда как общий когортный график показывает рост `spend/won` с ~€104 до €503.
   - Точка роста не убедительна в текущем виде; нужно использовать `ROAS` (48x Webinar vs 11x Google Ads) или пересчитать через `spend/won`.

6. **Дашборд не создан** — требуется по заданию (финальный артефакт).

7. **Презентация не создана** — требуется по заданию (финальный артефакт).

### 🟢 Мелкие (косметика / стиль)

8. **Воронка-чарт (08, ячейка exec=6)** — текст последнего бара (849, 4.6%) обрезан из-за малой ширины столбца.

9. **Когортный анализ (08, раздел 4.3)** — план требует pivot-таблицу `Cohort × Source`, реализован только суммарный aggregated по месяцу без разбивки по источникам.

10. **Воронка (08, раздел 4.2)** — план указывает `plotly go.Funnel`, реализовано на matplotlib (визуально корректно, но не интерактивно).

---

## ПЛАН РЕВЬЮ И ПРАВОК

### Приоритет 1 (обязательно перед защитой)
- [ ] Исправить расчёт Revenue потенциала в точке роста 3 (делить на 100)
- [ ] Пересчитать H1 с новым MDE, чтобы длительность ≤ 2 недели
- [ ] Пересчитать H2 с новым MDE, чтобы длительность ≤ 2 недели
- [ ] Добавить секцию 3.3.3 в 07_analysis.ipynb

### Приоритет 2 (желательно)
- [ ] Исправить точку роста 4 (Google Ads): использовать ROAS вместо CAC в €
- [ ] Исправить обрезку текста на воронке (ширина фигуры или font size)
- [ ] Добавить cohort pivot-таблицу по Source в 08

### Приоритет 3 (финальные артефакты)
- [ ] Создать дашборд (Plotly)
- [ ] Создать `report/presentation.pptx`
