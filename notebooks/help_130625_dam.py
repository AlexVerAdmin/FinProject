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
        if pd.isna(val) or val == '':
            return None
        s_val = str(val).split('.')[0] 
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

def descr_df(df, include='all', show=True, show_stats=True, show_sample_rows=False, show_quartiles=False):
    """
    Выводит расширенную информацию о датасете в табличном формате (универсальная EDA функция).
    """
    if include == 'all':
        filtered_df = df.copy()
    else:
        filtered_df = df.select_dtypes(include=include).copy()
    
    if filtered_df.empty:
        print(f"В датасете нет колонок с типом данных: {include}")
        return None
    
    info_dict = {
        'Признак': filtered_df.columns,
        'Тип': filtered_df.dtypes.values,
        'Заполнено': filtered_df.count().values,
        'Пропуски': filtered_df.isnull().sum().values,
        '% Пропусков': (filtered_df.isnull().sum() / len(df) * 100).round(2).values,
        'Уникальных': filtered_df.nunique(dropna=True).values
    }
    
    if show_sample_rows:
        for i in range(min(3, len(df))):
            info_dict[f'Пример {i+1}'] = filtered_df.iloc[i].values
    
    numeric_df = filtered_df.select_dtypes(include='number')
    if not numeric_df.empty:
        num_f = numeric_df.astype(float)
        if show_stats:
            info_dict['Min'] = numeric_df.min().reindex(filtered_df.columns).values
            info_dict['Mean'] = numeric_df.mean().round(2).reindex(filtered_df.columns).values
            info_dict['Median'] = numeric_df.median().reindex(filtered_df.columns).values
            info_dict['Max'] = numeric_df.max().reindex(filtered_df.columns).values
            info_dict['Range'] = (num_f.max() - num_f.min()).reindex(filtered_df.columns).values
        if show_quartiles:
            q25 = numeric_df.quantile(0.25)
            q75 = numeric_df.quantile(0.75)
            info_dict['Q1'] = q25.reindex(filtered_df.columns).values
            info_dict['Q3'] = q75.reindex(filtered_df.columns).values
            info_dict['IQR'] = (q75 - q25).reindex(filtered_df.columns).values
    
    result = pd.DataFrame(info_dict).set_index('Признак')
    if show:
        display(result)
        return None
    return result

def get_outliers_info(df, column, whisker=1.5):
    """
    Статистика по выбросам на основе IQR.
    """
    if not pd.api.types.is_numeric_dtype(df[column]):
        return "Колонка не числовая"
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - whisker * iqr
    upper_bound = q3 + whisker * iqr
    outliers = df[(df[column].astype(float) < lower_bound) | (df[column].astype(float) > upper_bound)]
    return {
        'column': column, 'q1': q1, 'q3': q3, 'iqr': iqr,
        'lower_bound': lower_bound, 'upper_bound': upper_bound,
        'outliers_count': len(outliers), 'outliers_percent': round(len(outliers) / len(df) * 100, 2)
    }

def compare_groups(df, target, group_col, show_plot=True):
    """
    Сравнение групп по целевому показателю (числовому или категориальному).
    """
    if pd.api.types.is_numeric_dtype(df[target]):
        stats_df = df.groupby(group_col)[target].agg(['count', 'mean', 'median', 'std', 'min', 'max']).round(2)
        if show_plot:
            plt.figure(figsize=(10, 5))
            sns.boxplot(data=df, x=group_col, y=target)
            plt.title(f'Распределение {target} по группам {group_col}')
            plt.show()
        return stats_df
    else:
        ct = pd.crosstab(df[group_col], df[target], normalize='index').round(4) * 100
        if show_plot:
            ct.plot(kind='bar', stacked=True, figsize=(10, 5))
            plt.title(f'Распределение {target} в группах {group_col} (%)')
            plt.legend(bbox_to_anchor=(1, 1))
            plt.show()
        return ct

def hist_box(column, df, title=None, discrete=False, bins='fd', hue=None, figsize=(FIG_WIDTH, FIG_HEIGHT), kde=False):
    """
    Гистограмма + Боксплот.
    """
    if title is None: title = column
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(2, 1, height_ratios=(4, 1), hspace=0.3)
    ax_hist = fig.add_subplot(gs[0])
    ax_box = fig.add_subplot(gs[1], sharex=ax_hist)
    sns.histplot(data=df, x=column, bins=bins, hue=hue, kde=kde, discrete=discrete, ax=ax_hist)
    ax_hist.set_title(title, fontsize=14, pad=15, color=COLOR_TEXT, fontweight='bold')
    ax_hist.set_xlabel('')
    sns.boxplot(data=df, x=column, hue=hue, ax=ax_box)
    ax_box.set_xlabel(column)
    plt.show()

def plot_top_n(df, column, n=10, title=None, figsize=(FIG_WIDTH, FIG_HEIGHT)):
    """
    Топ-N значений категориальной переменной.
    """
    top_data = df[column].value_counts().head(n)
    plt.figure(figsize=figsize)
    sns.barplot(x=top_data.values, y=top_data.index, palette='viridis')
    plt.title(title or f'Top {n} for {column}')
    plt.xlabel('Count')
    plt.show()
