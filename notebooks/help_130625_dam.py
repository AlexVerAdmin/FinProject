import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re
import math
from matplotlib.gridspec import GridSpec

from IPython.display import display
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

COLOR_TEXT = plt.get_cmap('PuBu')(0.85)  # color for subtitles
FIG_WIDTH = 10
FIG_HEIGHT = 5

def to_snake(col):
    """
    Преобразует строку в snake_case, убирая пробелы и скобки.
    """
    col = str(col).lower()
    col = re.sub(r'[\s\(\)]+', '_', col)
    return col.strip('_')

def str_to_int64(val):
    """
    Безопасное преобразование значения в Int64 (pandas nullable integer).
    Предотвращает потерю точности для 19-значных ID, избегая промежуточного float.
    """
    try:
        if pd.isna(val):
            return None
        # Если это уже число (но пришло как float/int), приводим к строке
        # Но лучше всего передавать сразу строку из read_excel(dtype=str)
        s_val = str(val).split('.')[0] # Убираем .0 если затесался float
        return int(s_val)
    except (ValueError, TypeError):
        return None

def clean_amount(series):
    """
    Очищает колонку с суммами: убирает пробелы, валюту, преобразует в float.
    """
    if series.dtype == 'object':
        series = series.astype(str).str.replace(r'[\s $€₽]+', '', regex=True).str.replace(',', '.')
    return pd.to_numeric(series, errors='coerce')

def descr_df(df, include='number', show=True, show_stats=True, show_sample_rows=False):
    """
    Выводит основную информацию о датасете в удобном табличном формате.
    
    Функция создает сводную таблицу с информацией о колонках: тип данных, 
    количество значений, пропуски, уникальные значения и статистики.
    
    Параметры:
    ----------
    df : pd.DataFrame
        Датафрейм для анализа
        
    include : str или list, default='number'
        Тип данных для фильтрации колонок (передается в select_dtypes):
        - 'number' - только числовые колонки
        - 'object' - только текстовые/категориальные колонки
        - ['number', 'object'] - или 'all' для всех типов
        
    show : bool, default=True
        Если True, выводит таблицу на экран
        Если False, возвращает DataFrame с результатами
        
    show_stats : bool, default=True
        Показывать ли описательные статистики (min, mean, median, max)
        Применяется только к числовым колонкам
        
    show_sample_rows : bool, default=False
        Показывать ли примеры значений из первых строк датасета
        Полезно для быстрой проверки содержимого
    
    Возвращает:
    ----------
    None или pd.DataFrame
        Если show=True, выводит таблицу и возвращает None
        Если show=False, возвращает DataFrame с информацией
    
    Примеры:
    --------
    >>> # Базовая информация о числовых колонках
    >>> desc_df(data)
    
    >>> # Информация о текстовых колонках без статистик
    >>> desc_df(data, include='object', show_stats=False)
    
    >>> # Подробная информация со всеми колонками и примерами значений
    >>> desc_df(data, include=['number', 'object'], show_sample_rows=True)
    """
    
    # Фильтруем колонки по типу данных
    if include == 'all':
        filtered_df = df.copy()
    else:
        filtered_df = df.select_dtypes(include=include).copy()
    
    if filtered_df.empty:
        print(f"В датасете нет колонок с типом данных: {include}")
        return None
    
    # Создаем словарь с базовой информацией
    info_dict = {}
    info_dict['Название признака'] = filtered_df.columns
    info_dict['Тип данных'] = filtered_df.dtypes.values
    info_dict['Количество значений'] = filtered_df.count().values
    info_dict['Пропуски (NaN)'] = filtered_df.isnull().sum().values
    info_dict['Уникальных значений'] = filtered_df.nunique(dropna=True).values
    
    # Добавляем примеры значений из первых строк (опционально)
    if show_sample_rows:
        SAMPLE_ROWS_COUNT = 3
        for i in range(min(SAMPLE_ROWS_COUNT, len(filtered_df))):
            info_dict[f'Пример строка {i+1}'] = filtered_df.iloc[i].values
    
    # Добавляем статистики для числовых колонок (опционально)
    if show_stats:
        numeric_df = filtered_df.select_dtypes(include='number')
        
        if not numeric_df.empty:
            # Используем reindex для корректного выравнивания со всеми колонками
            info_dict['Минимум'] = numeric_df.min().reindex(filtered_df.columns).values
            info_dict['Среднее'] = numeric_df.mean().reindex(filtered_df.columns).values
            info_dict['Медиана'] = numeric_df.median().reindex(filtered_df.columns).values
            info_dict['Максимум'] = numeric_df.max().reindex(filtered_df.columns).values
        else:
            # Если числовых колонок нет, заполняем прочерками или NaN для корректности DataFrame
            info_dict['Минимум'] = [np.nan] * len(filtered_df.columns)
            info_dict['Среднее'] = [np.nan] * len(filtered_df.columns)
            info_dict['Медиана'] = [np.nan] * len(filtered_df.columns)
            info_dict['Максимум'] = [np.nan] * len(filtered_df.columns)
    
    # Создаем итоговый DataFrame
    result_df = pd.DataFrame(info_dict)
    
    # Выводим или возвращаем результат
    if show:
        display(result_df)
        return None
    else:
        return result_df

def hist_box(column, df, title=None, discrete=False, bins='fd', hue=None, figsize=(FIG_WIDTH, FIG_HEIGHT), kde=False, p=1):
    """
    Визуализирует распределение числовой переменной с помощью гистограммы и ящика с усами.
    
    Функция создает комбинированный график:
    - Верхняя часть: гистограмма с кривой плотности (KDE)
    - Нижняя часть: диаграмма размаха (boxplot) для выявления выбросов
    
    Параметры:
    ----------
    column : str
        Название числовой колонки для анализа
        
    df : pd.DataFrame
        Датафрейм с данными
        
    title : str, optional
        Заголовок графика. Если не указан, используется название колонки
        
    bins : int или str, default='fd'
        Количество столбцов (bins) в гистограмме или метод расчета:
        - 'fd' (Freedman-Diaconis) - автоматический выбор (рекомендуется)
        - 'auto', 'sturges', 'scott' - другие автоматические методы
        - int (например, 30, 50) - точное количество bins
        
    hue : str, optional
        Название категориальной колонки для группировки данных
        Позволяет сравнить распределения разных групп на одном графике
        
    figsize : tuple, default=(FIG_WIDTH, FIG_HEIGHT)
        Размер графика (ширина, высота) в дюймах
    
    Примеры:
    --------
    >>> # Простое распределение цены
    >>> hist_box('Price', data, title='Цена автомобиля')
    
    >>> # Сравнение распределения цены по типу топлива
    >>> hist_box('Price', data, title='Цена по типу топлива', hue='FuelType')
    
    >>> # С фиксированным количеством bins
    >>> hist_box('Mileage', data, bins=50, title='Пробег автомобиля')
    """
    
    # Создаем фигуру и сетку для размещения графиков
    fig = plt.figure(figsize=figsize)
    n = 5  # отводим 5 строк для гистограммы 
    p = p  # строк для boxplot
    gs = GridSpec(ncols=1, nrows=n+p, figure=fig, hspace=0.05)
    
    # Заголовок по умолчанию
    if title is None:
        title = column
    
    # === ГИСТОГРАММА (верхняя часть) ===
    ax_hist = fig.add_subplot(gs[0:n, 0])
    
    if hue is None:
        # Простая гистограмма без группировки
        sns.histplot(
            data=df, 
            x=column, 
            bins=bins, 
            kde=kde,
            ax=ax_hist,
            alpha=0.6,
            discrete=discrete
        )
    else:
        # Гистограмма с группировкой по категории
        sns.histplot(
            data=df, 
            x=column, 
            hue=hue, 
            bins=bins, 
            kde=True, 
            ax=ax_hist,
            alpha=0.5
        )
        # Обращаемся к легенде, созданной seaborn, и задаём заголовок
        legend = ax_hist.get_legend()
        if legend:
            legend.set_title(hue)
    
    ax_hist.set_xlabel("")
    ax_hist.set_ylabel('Частота (количество)', fontsize=13)
    ax_hist.tick_params(axis='x', labelbottom=False)
    ax_hist.tick_params(axis='y', labelsize=12)
    ax_hist.grid(axis='y', alpha=0.3, linestyle='--')
    
    # === BOXPLOT (нижняя часть) ===
    ax_box = fig.add_subplot(gs[n:n+p, 0])
    
    if hue is None:
        # Простой boxplot
        sns.boxplot(
            data=df, 
            x=column, 
            ax=ax_box,
            width=0.3
        )
    else:
        # Boxplot с группировкой и цветами по группам
        sns.boxplot(
            data=df,
            x=column,
            y=hue,
            hue=hue,
            ax=ax_box,
            legend=False,
        )
    
    ax_box.set_xlabel(column, fontsize=13)
    ax_box.tick_params(axis='both', labelsize=12)
    ax_box.grid(axis='x', alpha=0.3, linestyle='--')
    

    plt.suptitle(f'Гистограмма и бокс-плот для \"{title}\"', fontsize=16, color=COLOR_TEXT)
    plt.subplots_adjust(top=0.92)
    plt.show()

def iqr_outliers(column, df, coef=1.5,  show=True):
    """
    Определяет границы и количество выбросов методом межквартильного размаха (IQR).

    Метод IQR (Interquartile Range):
    - Вычисляет 25-й (Q1) и 75-й (Q3) процентили
    - IQR = Q3 - Q1
    - Нижняя граница: Q1 - 1.5(coef) * IQR
    - Верхняя граница: Q3 + 1.5(coef) * IQR
    - Значения за пределами этих границ считаются выбросами

    Параметры:
    ----------
    column : str
        Название числовой колонки для анализа

    df : pd.DataFrame
        Датафрейм с данными

    show : bool, default=True
        Если True, выводит таблицу с результатами на экран
        Если False, возвращает DataFrame с результатами

    Возвращает:
    ----------
    None или pd.DataFrame
        Если show=True, выводит таблицу и возвращает None
        Если show=False, возвращает DataFrame с информацией о выбросах
    """
    series = df[column].dropna().copy()
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    left_border = q1 - coef * iqr
    right_border = q3 + coef * iqr

    outlier_count_left = (series < left_border).sum()
    outlier_count_right = (series > right_border).sum()
    total = len(series)

    result_dict = {
        'Границы выбросов': [left_border, right_border],
        'Количество выбросов': [outlier_count_left, outlier_count_right],
        'Процент выбросов': [round(outlier_count_left / total * 100, 2), round(outlier_count_right / total * 100, 2)]
    }

    outlier_df = pd.DataFrame.from_dict(result_dict, orient='index', columns=['Слева', 'Справа'])

    if show:
        display(outlier_df)
    else:
        return outlier_df

def plot_pdf_cdf_with_threshold(
    pdf_func,
    cdf_func,
    x_range,
    threshold,
    title="PDF and CDF",
        same_ylims=False
):
    """
    Рисует PDF и CDF на одном графике
    и вертикальную линию в заданной точке threshold.
    
    pdf_func - функция плотности (должна принимать массив x)
    cdf_func - функция распределения (должна принимать массив x)
    x_range  - кортеж (xmin, xmax)
    threshold - вертикальная точка
    """

    x = np.linspace(x_range[0], x_range[1], 1000)

    pdf_values = pdf_func(x)
    cdf_values = cdf_func(x)

    fig, ax1 = plt.subplots(figsize=(10, 4))

    # CDF
    line1, = ax1.plot(x, cdf_values, label="CDF", color='r')
    ax1.set_ylabel("CDF  P(X ≤ x)")
    ax1.set_xlabel("x")

    # PDF
    ax2 = ax1.twinx()
    line2, = ax2.plot(x, pdf_values, linestyle="--", label="PDF", color='b')
    ax2.set_ylabel("PDF (density)")
    if same_ylims:
        ax2.set_ylim(ax1.get_ylim())

    # вертикальная линия
    ax1.axvline(threshold, linestyle=":", linewidth=2, color='black')

    # вероятность справа
    prob_right = 1 - cdf_func(threshold)
    delta_x = (x_range[1] - x_range[0]) * 0.02
    ax1.text(
        threshold+delta_x,
        0.1,
        f"P(X > {threshold}) = {prob_right:.3f}",
        rotation=90,
        verticalalignment="bottom"
    )

    plt.title(title)
    ax1.legend([line1, line2], ["CDF", "PDF"])
    ax1.grid(alpha=0.3)

    plt.show()


def pair_cat(column, df, title=None, hue=None, kde=True, figsize=None):
    """
    Строит треугольный pair plot для числовой переменной.

    Переменные (столбцы/строки матрицы):
    - Первая: вся выборка (column целиком)
    - Остальные: column в разрезе каждой категории hue

    На диагонали — KDE, ниже диагонали — scatter + линия регрессии + r Пирсона.
    Верхний треугольник скрыт (corner-режим).

    Параметры:
    ----------
    column : str
        Название числовой колонки для анализа

    df : pd.DataFrame
        Датафрейм с данными

    title : str, optional
        Заголовок графика. Если не указан, используется название колонки

    hue : str, optional
        Категориальная колонка для разбивки на группы

    figsize : tuple, optional
        Размер графика. По умолчанию: (n*3.5, n*3.5), где n — число переменных

    Пример:
    -------
    >>> h.pair_cat('Price_log1p', data, title='для Price_log1p по типу топлива', hue='Fuel_Type')
    """
    if title is None:
        title = column

    # Собираем серии:
    # - по одной на каждую категорию hue (значения column для этой категории)
    # - предпоследний: сам hue-столбец числово закодированный (≠ column, r ≠ 1)
    # - последний: полный column (target_col) без разбивки
    labels = []
    series_list = []

    if hue is not None:
        for cat in sorted(df[hue].dropna().unique()):
            cat_vals = df.loc[df[hue] == cat, column].dropna().reset_index(drop=True)
            labels.append(str(cat))
            series_list.append(cat_vals)

        # hue закодированный числами (0, 1, 2, ...) — предпоследний
        base = df[[column, hue]].dropna().reset_index(drop=True)
        hue_codes = pd.Series(pd.Categorical(base[hue]).codes, name=hue)
        labels.append(hue)
        series_list.append(hue_codes)

    # target_col (полный, без разбивки) — последний
    labels.append(column)
    series_list.append(df[column].dropna().reset_index(drop=True))

    # Формируем широкий DataFrame с выравниванием по NaN
    max_len = max(len(s) for s in series_list)
    data_dict = {}
    for label, s in zip(labels, series_list):
        if len(s) < max_len:
            s = pd.concat([s, pd.Series([np.nan] * (max_len - len(s)))], ignore_index=True)
        data_dict[label] = s
    wide = pd.DataFrame(data_dict)

    n = len(labels)
    if figsize is None:
        figsize = (n * 3.5, n * 3.5)

    palette = sns.color_palette(n_colors=n)

    fig, axes = plt.subplots(n, n, figsize=figsize)
    if n == 1:
        axes = np.array([[axes]])

    for i in range(n):
        for j in range(n):
            ax = axes[i, j]

            if j > i:
                ax.set_visible(False)
                continue

            x_label = labels[j]
            y_label = labels[i]

            if i == j:
                # Диагональ — гистограмма + KDE поверх
                valid = wide[x_label].dropna()
                sns.histplot(data=valid, ax=ax, color=palette[i], alpha=0.4, kde=kde)
            else:
                # Нижний треугольник — scatter + регрессия + r Пирсона
                valid = wide[[x_label, y_label]].dropna()
                if len(valid) > 1:
                    sns.regplot(
                        data=valid, x=x_label, y=y_label, ax=ax,
                        scatter_kws={'alpha': 0.4, 's': 15, 'color': palette[j]},
                        line_kws={'color': 'red', 'linewidth': 1.5}
                    )
                    corr = valid[x_label].corr(valid[y_label])
                    ax.annotate(
                        f'r = {corr:.2f}',
                        xy=(0.05, 0.97), xycoords='axes fraction',
                        ha='left', va='top', fontsize=9,
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
                    )

            # Подписи осей
            if i == n - 1:
                ax.set_xlabel(x_label, fontsize=10)
            else:
                ax.set_xlabel('')
                ax.tick_params(labelbottom=False)

            if j == 0:
                ax.set_ylabel(y_label, fontsize=10)
            else:
                ax.set_ylabel('')
                ax.tick_params(labelleft=False)

    plt.suptitle(f'Pair Plot {title}', fontsize=14, color=COLOR_TEXT)
    plt.subplots_adjust(top=0.95, hspace=0.1, wspace=0.1)
    plt.show()


def catboost_encode(cat_col, target_col, df, a=1, n_permutations=1, random_state=42):
    """
    Кодирование категориального признака методом CatBoost (Ordered Target Encoding).

    Алгоритм (как в CatBoost):
    - Строки случайно переставляются
    - Для каждого наблюдения i кодированное значение вычисляется только
      по наблюдениям, которые идут ДО него в перестановке:

        TS(i) = (Σ target[j < i, cat[j] == cat[i]] + a * P)
                / (count[j < i, cat[j] == cat[i]] + a)

    Где P — глобальное среднее target, a — сглаживающий параметр.
    Это исключает утечку целевой переменной (target leakage).

    Параметры:
    ----------
    cat_col : str
        Название категориального столбца

    target_col : str
        Название целевого (числового) столбца

    df : pd.DataFrame
        Датафрейм с данными

    a : float, default=1
        Сглаживающий параметр (prior weight).
        Чем больше — тем сильнее тяготение к глобальному среднему для редких категорий.

    n_permutations : int, default=1
        Количество случайных перестановок. При > 1 результаты усредняются
        (снижает дисперсию, как в CatBoost с несколькими деревьями).

    random_state : int, default=42
        Начальное значение генератора случайных чисел

    Возвращает:
    ----------
    pd.Series
        Закодированные значения с тем же индексом, что и df.
        Название серии: '{cat_col}_cb_enc'

    Пример:
    -------
    >>> df['Fuel_Type_enc'] = h.catboost_encode('Fuel_Type', 'Price', df)
    """
    rng = np.random.default_rng(random_state)
    prior = df[target_col].mean()
    n = len(df)

    result = np.zeros(n)

    for _ in range(n_permutations):
        perm = rng.permutation(n)
        inv_perm = np.argsort(perm)

        cats = df[cat_col].values[perm]
        targets = df[target_col].values[perm]

        encoded = np.empty(n)
        cat_sum = {}
        cat_count = {}

        for i in range(n):
            cat = cats[i]
            s = cat_sum.get(cat, 0.0)
            c = cat_count.get(cat, 0)
            encoded[i] = (s + a * prior) / (c + a)
            cat_sum[cat] = s + targets[i]
            cat_count[cat] = c + 1

        result += encoded[inv_perm]

    result /= n_permutations
    return pd.Series(result, index=df.index, name=f'{cat_col}_cb_enc')


def plot_pdf_cdf_two_thresholds(
    pdf_func,
    cdf_func,
    x_range,
    threshold1,
    threshold2,
    title="PDF and CDF",
    same_ylims=False
):
    """
    Рисует PDF и CDF и две вертикальные линии.
    
    threshold1 - первая точка (например 5)
    threshold2 - вторая точка (например 10)
    """

    x = np.linspace(x_range[0], x_range[1], 1000)

    pdf_values = pdf_func(x)
    cdf_values = cdf_func(x)

    fig, ax1 = plt.subplots(figsize=(10, 4))

    # CDF
    line1, = ax1.plot(x, cdf_values, label="CDF", color='r')
    ax1.set_ylabel("CDF  P(X ≤ x)")
    ax1.set_xlabel("x")

    # PDF
    ax2 = ax1.twinx()
    line2, = ax2.plot(x, pdf_values, linestyle="--", label="PDF", color='b')
    ax2.set_ylabel("PDF (density)")
    if same_ylims:
        ax2.set_ylim(ax1.get_ylim())

    # вертикальные линии
    ax1.axvline(threshold1, linestyle=":", linewidth=2, color='black')
    ax1.axvline(threshold2, linestyle=":", linewidth=2, color='black')

    # вероятности
    sf = lambda x_val: 1 - cdf_func(x_val)

    prob_gt_5 = sf(threshold1)
    prob_gt_10_given_5 = sf(threshold2) / sf(threshold1)

    delta_x = (x_range[1] - x_range[0]) * 0.02

    ax1.text(
        threshold1 + delta_x,
        0.2,
        f"P(X > {threshold1}) = {prob_gt_5:.3f}",
        rotation=90,
        verticalalignment="bottom"
    )

    ax1.text(
        threshold2 + delta_x,
        0.4,
        f"P(X > {threshold2} | X > {threshold1}) = {prob_gt_10_given_5:.3f}",
        rotation=90,
        verticalalignment="bottom"
    )

    plt.title(title)
    ax1.legend([line1, line2], ["CDF", "PDF"])
    ax1.grid(alpha=0.3)

    plt.show()



def visualize_two_sample_test(sample1, sample2, test_result, 
                               label1='Group 1', label2='Group 2',
                               test_type='t-test', alpha=0.05):
    """
    Визуализация результатов двухвыборочного теста.
    
    Parameters:
        sample1, sample2: данные выборок
        test_result: кортеж (statistic, p_value)
        label1, label2: названия групп
        test_type: тип теста ('t-test' или 'z-test')
        alpha: уровень значимости
    """
    statistic, p_value = test_result
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # График 1: Гистограммы распределений
    ax1 = axes[0]
    ax1.hist(sample1, bins='fd', alpha=0.6, label=label1, color='skyblue', edgecolor='black')
    ax1.hist(sample2, bins='fd', alpha=0.6, label=label2, color='salmon', edgecolor='black')
    ax1.axvline(np.mean(sample1), color='blue', linestyle='--', linewidth=2, 
                label=f'Mean {label1}: {np.mean(sample1):.2f}')
    ax1.axvline(np.mean(sample2), color='red', linestyle='--', linewidth=2,
                label=f'Mean {label2}: {np.mean(sample2):.2f}')
    ax1.set_xlabel('Значение')
    ax1.set_ylabel('Частота')
    ax1.set_title('Распределения двух групп')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # График 2: Box plots для сравнения
    ax2 = axes[1]
    box_data = [sample1, sample2]
    bp = ax2.boxplot(box_data, labels=[label1, label2], patch_artist=True,
                     boxprops=dict(facecolor='lightblue', alpha=0.6),
                     medianprops=dict(color='red', linewidth=2))
    ax2.set_ylabel('Значение')
    ax2.set_title('Сравнение групп (Box Plot)')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Добавляем текст с результатами теста
    result_text = f'{test_type}\n'
    result_text += f'Статистика: {statistic:.4f}\n'
    result_text += f'P-value: {p_value:.6f}\n'
    result_text += f'α = {alpha}\n\n'
    
    if p_value < alpha:
        result_text += 'Отвергаем H0\n(различия значимы)'
        color = 'green'
    else:
        result_text += 'Не отвергаем H0\n(различия незначимы)'
        color = 'red'
    
    ax2.text(0.35, 0.98, result_text, transform=ax2.transAxes,
             fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor=color, alpha=0.2))
    
    plt.tight_layout()
    plt.show()


def visualize_paired_test(before, after, test_result, alpha=0.05):
    """
    Визуализация результатов парного теста.
    
    Parameters:
        before, after: данные до и после
        test_result: кортеж (statistic, p_value)
        alpha: уровень значимости
    """
    statistic, p_value = test_result
    differences = after - before
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # График 1: До vs После
    ax1 = axes[0]
    x_positions = np.arange(len(before))
    ax1.scatter(x_positions, before, alpha=0.5, label='До', color='blue', s=50)
    ax1.scatter(x_positions, after, alpha=0.5, label='После', color='red', s=50)
    for i in range(len(before)):
        ax1.plot([i, i], [before[i], after[i]], 'k-', alpha=0.2)
    ax1.axhline(np.mean(before), color='blue', linestyle='--', linewidth=2,
                label=f'Среднее До: {np.mean(before):.2f}')
    ax1.axhline(np.mean(after), color='red', linestyle='--', linewidth=2,
                label=f'Среднее После: {np.mean(after):.2f}')
    ax1.set_xlabel('Участник')
    ax1.set_ylabel('Значение')
    ax1.set_title('Сравнение До и После')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # График 2: Гистограмма разностей
    ax2 = axes[1]
    ax2.hist(differences, bins=20, alpha=0.7, color='purple', edgecolor='black')
    ax2.axvline(0, color='black', linestyle='-', linewidth=2, label='Нет изменений')
    ax2.axvline(np.mean(differences), color='red', linestyle='--', linewidth=2,
                label=f'Средняя разность: {np.mean(differences):.2f}')
    ax2.set_xlabel('Разность (После - До)')
    ax2.set_ylabel('Частота')
    ax2.set_title('Распределение разностей')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # График 3: Box plot разностей
    ax3 = axes[2]
    ax3.boxplot(differences, patch_artist=True,
                boxprops=dict(facecolor='lightgreen', alpha=0.6),
                medianprops=dict(color='red', linewidth=2))
    ax3.axhline(0, color='black', linestyle='--', linewidth=2, alpha=0.5)
    ax3.set_ylabel('Разность (После - До)')
    ax3.set_title('Box Plot разностей')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Результаты теста
    result_text = f'Парный тест\n'
    result_text += f'Статистика: {statistic:.4f}\n'
    result_text += f'P-value: {p_value:.6f}\n'
    result_text += f'α = {alpha}\n\n'
    
    if p_value < alpha:
        result_text += 'Отвергаем H0\n(изменения значимы)'
        color = 'green'
    else:
        result_text += 'Не отвергаем H0\n(изменения незначимы)'
        color = 'red'
    
    ax3.text(0.25, 0.98, result_text, transform=ax3.transAxes,
             fontsize=11, verticalalignment='top', horizontalalignment='center',
             bbox=dict(boxstyle='round', facecolor=color, alpha=0.2))
    
    plt.tight_layout()
    plt.show()


def ab_sample_size(p_base, mde_relative, alpha=0.05, power=0.8):
    """
    Рассчитывает размер выборки для одной группы в A/B тесте.
    Основано на Z-тесте для пропорций (статистика statsmodels).
    
    Параметры:
    ----------
    p_base : float
        Базовая конверсия (от 0 до 1)
    mde_relative : float
        Относительный минимальный детектируемый эффект (MDE), например 0.10 для +10%
    alpha : float, default=0.05
        Уровень значимости
    power : float, default=0.8
        Мощность теста (1 - beta)
        
    Возвращает:
    ----------
    int
        Необходимый размер выборки для ОДНОЙ группы
    """
    p_target = p_base * (1 + mde_relative)
    # Cohen's h effect size
    effect_size = proportion_effectsize(p_base, p_target)
    analysis = NormalIndPower()
    
    # Решаем уравнение для n
    n = analysis.solve_power(
        effect_size=effect_size, 
        alpha=alpha, 
        power=power, 
        ratio=1.0, 
        alternative='two-sided'
    )
    return int(math.ceil(n))
