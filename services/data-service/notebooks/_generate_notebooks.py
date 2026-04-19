"""Generate all data-quality notebooks. Run: python _generate_notebooks.py"""

import json
from pathlib import Path

OUT = Path(__file__).parent
DATA = "../data/processed/export"


def nb(cells):
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }


_cell_counter = [0]


def _uid():
    _cell_counter[0] += 1
    return f"cell{_cell_counter[0]:04d}"


def md(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.strip(),
        "id": _uid(),
    }


def code(src):
    return {
        "cell_type": "code",
        "metadata": {},
        "source": src.strip(),
        "outputs": [],
        "execution_count": None,
        "id": _uid(),
    }


def save(name, cells):
    path = OUT / name
    path.write_text(json.dumps(nb(cells), indent=1, ensure_ascii=False))
    print(f"  {name}")


# ── SETUP cell reused in every notebook ─────────────────────────────────────
SETUP = """\
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings, os
warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams.update({'figure.dpi': 130, 'figure.figsize': (12, 5)})

DATA = os.path.join(os.path.dirname(os.path.abspath('.')), 'data/processed/export')
def load(name): return pd.read_csv(f'{DATA}/{name}.csv')
"""

# ════════════════════════════════════════════════════════════════════════════
# 1. DESTINATIONS
# ════════════════════════════════════════════════════════════════════════════
save(
    "05_destinations.ipynb",
    [
        md("# Destinations — Coverage & Distribution"),
        code(SETUP),
        code("""\
df = load('destinations')
print(f"Total: {len(df)}  |  active: {df['is_active'].sum()}")
df[['name','country_code','region','subregion','population','lat','lng']].head(10)
"""),
        md("## Regional breakdown"),
        code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

region_counts = df['region'].value_counts()
axes[0].barh(region_counts.index, region_counts.values, color=sns.color_palette('muted', len(region_counts)))
axes[0].set_title('Destinations by Region')
axes[0].set_xlabel('Count')

sub = df['subregion'].value_counts().head(15)
axes[1].barh(sub.index, sub.values)
axes[1].set_title('Top 15 Subregions')
axes[1].set_xlabel('Count')
plt.tight_layout(); plt.show()
print(df['region'].value_counts().to_string())
"""),
        md("## World map scatter"),
        code("""\
fig, ax = plt.subplots(figsize=(15, 7))
colors = df['region'].astype('category').cat.codes
ax.scatter(df['lng'], df['lat'], c=colors, cmap='tab10', s=18, alpha=0.75)
for _, row in df[df['population'] > 8_000_000].iterrows():
    ax.annotate(row['name'], (row['lng'], row['lat']), fontsize=6, alpha=0.7)
ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude')
ax.set_title('394 Destinations — World Map')
plt.tight_layout(); plt.show()
"""),
        md("## Population distribution"),
        code("""\
pop = df[df['population'] > 0]['population'] / 1e6
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].hist(pop, bins=40, edgecolor='white')
axes[0].set_xlabel('Population (M)'); axes[0].set_title('Population histogram')
axes[1].hist(pop[pop < 5], bins=40, edgecolor='white', color='steelblue')
axes[1].set_xlabel('Population (M) — zoomed < 5M'); axes[1].set_title('Zoomed < 5M')
plt.tight_layout(); plt.show()
print(f"Median population: {pop.median():.2f}M  |  Max: {pop.max():.1f}M ({df.loc[pop.idxmax(),'name']})")
print(f"Destinations without population: {(df['population']==0).sum()}")
"""),
        md("## Special destinations added manually"),
        code("""\
special = df[df['name'].isin(['Machu Picchu','Yellowstone','Serengeti','Malé'])]
special[['name','country_code','lat','lng','population','region']]
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 2. SAFETY
# ════════════════════════════════════════════════════════════════════════════
save(
    "06_safety.ipynb",
    [
        md("# Destination Safety — GPI-Based Scores"),
        code(SETUP),
        code("""\
df = load('destination_safety')
dests = load('destinations')[['id','name','country_code','region']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Records: {len(df)}  |  with GPI: {df['gpi_score'].notna().sum()}  |  defaults: {df['gpi_score'].isna().sum()}")
df[['name','country_code','safety_score','gpi_score','gpi_rank']].sort_values('safety_score').head(10)
"""),
        md("## Score distribution"),
        code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].hist(df['safety_score'], bins=30, edgecolor='white', color='steelblue')
axes[0].axvline(0.5, color='orange', linestyle='--', label='default (0.5)')
axes[0].set_xlabel('safety_score'); axes[0].set_title('Safety Score Distribution')
axes[0].legend()

region_avg = df.groupby('region')['safety_score'].mean().sort_values()
axes[1].barh(region_avg.index, region_avg.values,
             color=sns.color_palette('RdYlGn', len(region_avg)))
axes[1].set_xlabel('avg safety_score'); axes[1].set_title('Average by Region')
plt.tight_layout(); plt.show()
"""),
        md("## Most and least safe destinations"),
        code("""\
print("=== TOP 10 SAFEST ===")
print(df.nlargest(10, 'safety_score')[['name','country_code','safety_score','gpi_rank']].to_string(index=False))
print()
print("=== 10 LEAST SAFE ===")
print(df.nsmallest(10, 'safety_score')[['name','country_code','safety_score','gpi_rank']].to_string(index=False))
"""),
        md("## GPI score vs safety_score — normalization check"),
        code("""\
gpi = df.dropna(subset=['gpi_score'])
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(gpi['gpi_score'], gpi['safety_score'], alpha=0.5, s=15)
ax.set_xlabel('GPI score (lower = safer)')
ax.set_ylabel('safety_score (higher = safer)')
ax.set_title('GPI → safety_score normalization (should be inverse)')
plt.tight_layout(); plt.show()
corr = gpi[['gpi_score','safety_score']].corr().iloc[0,1]
print(f"Pearson correlation: {corr:.3f}  (expected ~ -1.0)")
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 3. COSTS
# ════════════════════════════════════════════════════════════════════════════
save(
    "07_costs.ipynb",
    [
        md("# Destination Costs — Numbeo + Regional Averages"),
        code(SETUP),
        code("""\
df = load('destination_costs')
dests = load('destinations')[['id','name','country_code','region','subregion']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Records: {len(df)}")
print(df['data_source'].value_counts().to_string())
df[['name','avg_daily_cost_usd','cost_index','data_source']].sort_values('avg_daily_cost_usd', ascending=False).head(10)
"""),
        md("## data_source coverage"),
        code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
src_counts = df['data_source'].value_counts()
axes[0].pie(src_counts.values, labels=src_counts.index, autopct='%1.0f%%',
            colors=sns.color_palette('pastel'))
axes[0].set_title('Data Source Coverage')

src_avg = df.groupby('data_source')['avg_daily_cost_usd'].mean().sort_values()
axes[1].barh(src_avg.index, src_avg.values)
axes[1].set_xlabel('avg daily cost (USD)'); axes[1].set_title('Avg Daily Cost by Source')
plt.tight_layout(); plt.show()
"""),
        md("## Daily cost distribution"),
        code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
real = df[df['data_source']=='numbeo']
axes[0].hist(real['avg_daily_cost_usd'], bins=30, edgecolor='white', color='steelblue', label='Numbeo')
axes[0].hist(df[df['data_source']!='numbeo']['avg_daily_cost_usd'], bins=30,
             edgecolor='white', alpha=0.6, color='orange', label='Estimated')
axes[0].set_xlabel('avg_daily_cost_usd'); axes[0].set_title('Daily Cost Distribution')
axes[0].legend()

region_cost = df.groupby('region')['avg_daily_cost_usd'].median().sort_values()
axes[1].barh(region_cost.index, region_cost.values)
axes[1].set_xlabel('Median daily cost (USD)'); axes[1].set_title('Median Cost by Region')
plt.tight_layout(); plt.show()
"""),
        md("## Most expensive vs cheapest"),
        code("""\
numbeo = df[df['data_source'] == 'numbeo'].copy()
print("=== TOP 10 MOST EXPENSIVE (Numbeo data only) ===")
print(numbeo.nlargest(10,'avg_daily_cost_usd')[['name','avg_daily_cost_usd','cost_index']].to_string(index=False))
print()
print("=== TOP 10 CHEAPEST ===")
print(numbeo.nsmallest(10,'avg_daily_cost_usd')[['name','avg_daily_cost_usd','cost_index']].to_string(index=False))
"""),
        md("## Cost components breakdown (Numbeo)"),
        code("""\
components = ['avg_meal_cost_usd','avg_transport_cost_usd','avg_hotel_cost_usd']
comp_avg = numbeo[components].mean()
fig, ax = plt.subplots(figsize=(6, 4))
comp_avg.plot.bar(ax=ax, color=['#4C72B0','#DD8452','#55A868'], edgecolor='white')
ax.set_title('Average Cost Components (Numbeo destinations)')
ax.set_ylabel('USD / day')
ax.set_xticklabels(['Meals (×2.5)', 'Transport', 'Hotel'], rotation=0)
plt.tight_layout(); plt.show()
print(f"Formula: meal×2.5 + transport + hotel = avg_daily_cost_usd")
print(f"Check sample: {comp_avg['avg_meal_cost_usd']:.1f}×2.5 + {comp_avg['avg_transport_cost_usd']:.1f} + {comp_avg['avg_hotel_cost_usd']:.1f} = {comp_avg['avg_meal_cost_usd']*2.5+comp_avg['avg_transport_cost_usd']+comp_avg['avg_hotel_cost_usd']:.1f}")
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 4. SEASONALITY
# ════════════════════════════════════════════════════════════════════════════
save(
    "08_seasonality.ipynb",
    [
        md("# Seasonality — season_score with Temperature + Precipitation + Humidity"),
        code(SETUP),
        code("""\
df = load('destination_seasonality')
dests = load('destinations')[['id','name','country_code','region','subregion','lat']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Records: {len(df)}  |  with humidity: {df['avg_humidity_pct'].notna().sum()}")
print(f"season_score range: [{df['season_score'].min():.3f} – {df['season_score'].max():.3f}]")
print(f"avg: {df['season_score'].mean():.3f}")
"""),
        md("## Heatmap: season_score for selected cities"),
        code("""\
CITIES = ['Bangkok','Phuket','Bali','Dubai','Singapore',
          'Paris','London','Tokyo','Sydney','Cape Town',
          'Reykjavik','Cancun','New York','Buenos Aires','Nairobi']

pivot = df[df['name'].isin(CITIES)].pivot_table(
    index='name', columns='month', values='season_score')
pivot.columns = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

fig, ax = plt.subplots(figsize=(14, 6))
sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn', vmin=0, vmax=1,
            linewidths=0.5, ax=ax, cbar_kws={'label': 'season_score'})
ax.set_title('Season Score by Month (green = great, red = avoid)')
ax.set_xlabel(''); ax.set_ylabel('')
plt.tight_layout(); plt.show()
"""),
        md("## Tropical cities: dry vs wet season contrast"),
        code("""\
tropical = ['Bangkok','Phuket','Bali','Singapore','Cancun','Mumbai','Jakarta','Ho Chi Minh City']
trop_df = df[df['name'].isin(tropical) & df['name'].isin(df['name'].unique())]

if len(trop_df) > 0:
    pivot_t = trop_df.pivot_table(index='name', columns='month', values='season_score')
    spread = pivot_t.max(axis=1) - pivot_t.min(axis=1)
    print("Tropical seasonal spread (max - min season_score):")
    print(spread.sort_values(ascending=False).to_string())
"""),
        md("## Temperature vs humidity vs score scatter"),
        code("""\
sample = df[df['avg_humidity_pct'].notna()].sample(min(2000, len(df)), random_state=42)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

sc1 = axes[0].scatter(sample['avg_temp_c'], sample['season_score'],
               c=sample['avg_precipitation_mm'], cmap='RdYlBu_r', s=8, alpha=0.5)
plt.colorbar(sc1, ax=axes[0], label='precipitation (mm/month)')
axes[0].set_xlabel('avg_temp_c'); axes[0].set_ylabel('season_score')
axes[0].set_title('Temp vs Score (colour = precipitation)')

sc2 = axes[1].scatter(sample['avg_humidity_pct'], sample['season_score'],
               c=sample['avg_temp_c'], cmap='RdYlBu_r', s=8, alpha=0.5)
plt.colorbar(sc2, ax=axes[1], label='temperature (°C)')
axes[1].set_xlabel('avg_humidity_pct'); axes[1].set_ylabel('season_score')
axes[1].set_title('Humidity vs Score (colour = temperature)')
plt.tight_layout(); plt.show()
"""),
        md("## Best month per destination by region"),
        code("""\
best = df.loc[df.groupby('destination_id')['season_score'].idxmax()][['name','month','season_score','region']]
month_names = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
               7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
best['month_name'] = best['month'].map(month_names)

fig, ax = plt.subplots(figsize=(12, 4))
month_dist = best['month'].value_counts().reindex(range(1,13), fill_value=0)
ax.bar(month_names.values(), month_dist.values, color=sns.color_palette('tab20', 12))
ax.set_title('Best month distribution across all 394 destinations')
ax.set_xlabel('Month'); ax.set_ylabel('# destinations')
plt.tight_layout(); plt.show()
print("\\nBest months by region:")
print(best.groupby('region')['month_name'].agg(lambda x: x.value_counts().index[0]).to_string())
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 5. ACTIVITIES
# ════════════════════════════════════════════════════════════════════════════
save(
    "09_activities.ipynb",
    [
        md("# Destination Activities — POI-Based Scores per Category"),
        code(SETUP),
        code("""\
df = load('destination_activities')
dests = load('destinations')[['id','name','country_code','region']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Records: {len(df)}  |  unique destinations: {df['destination_id'].nunique()}")
df.groupby('activity_type').agg(
    destinations=('destination_id','count'),
    nonzero=('score', lambda x: (x>0).sum()),
    avg_score=('score','mean'),
    avg_poi=('poi_count','mean')
).round(3).sort_values('avg_score', ascending=False)
"""),
        md("## Score distributions per activity type"),
        code("""\
types = df['activity_type'].unique()
fig, axes = plt.subplots(2, 5, figsize=(18, 7))
axes = axes.flatten()
for i, atype in enumerate(sorted(types)):
    sub = df[df['activity_type']==atype]['score']
    axes[i].hist(sub[sub>0], bins=20, edgecolor='white', color=f'C{i}')
    axes[i].set_title(f'{atype}\\navg={sub.mean():.3f}  n={len(sub)}')
    axes[i].set_xlim(0, 1)
plt.suptitle('Score Distributions by Activity Type (nonzero only)', y=1.01)
plt.tight_layout(); plt.show()
"""),
        md("## Radar chart: activity profile for top tourist cities"),
        code("""\
import numpy as np

CITIES = ['Paris','Bangkok','Bali','Dubai','New York','Tokyo','Barcelona','Cape Town']
pivot = df[df['name'].isin(CITIES)].pivot_table(index='name', columns='activity_type', values='score').fillna(0)
pivot = pivot[[c for c in sorted(pivot.columns)]]

categories = list(pivot.columns)
N = len(categories)
angles = [n / float(N) * 2 * np.pi for n in range(N)] + [0]

fig, axes = plt.subplots(2, 4, figsize=(16, 8), subplot_kw=dict(polar=True))
axes = axes.flatten()

for i, city in enumerate(pivot.index[:8]):
    vals = list(pivot.loc[city]) + [list(pivot.loc[city])[0]]
    axes[i].plot(angles, vals, linewidth=1.5, linestyle='solid', color=f'C{i}')
    axes[i].fill(angles, vals, alpha=0.25, color=f'C{i}')
    axes[i].set_xticks(angles[:-1])
    axes[i].set_xticklabels(categories, size=7)
    axes[i].set_ylim(0, 1)
    axes[i].set_title(city, size=10, pad=10)

plt.suptitle('Activity Profiles (radar chart)', y=1.01)
plt.tight_layout(); plt.show()
"""),
        md("## Top 10 destinations per activity type"),
        code("""\
for atype in ['beach','wellness','culture','nature','food']:
    top = df[df['activity_type']==atype].nlargest(8,'score')[['name','country_code','score','poi_count']]
    print(f"\\n=== TOP {atype.upper()} ===")
    print(top.to_string(index=False))
"""),
        md("## Coverage heatmap: which activities are present per destination"),
        code("""\
top50 = df.groupby('destination_id')['score'].mean().nlargest(50).index
sub = df[df['destination_id'].isin(top50)]
pivot_cov = sub.pivot_table(index='name', columns='activity_type', values='score').fillna(0)

fig, ax = plt.subplots(figsize=(14, 14))
sns.heatmap(pivot_cov.sort_values('culture', ascending=False),
            cmap='YlOrRd', vmin=0, vmax=0.5, ax=ax,
            linewidths=0.3, cbar_kws={'label': 'activity score'})
ax.set_title('Activity Scores — Top 50 Destinations')
ax.set_xlabel(''); ax.set_ylabel('')
plt.tight_layout(); plt.show()
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 6. POPULARITY
# ════════════════════════════════════════════════════════════════════════════
save(
    "10_popularity.ipynb",
    [
        md("# Destination Popularity — Wikipedia Pageviews + crowd_index"),
        code(SETUP),
        code("""\
df = load('destination_popularity')
dests = load('destinations')[['id','name','country_code','region']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Records: {len(df)}  |  destinations: {df['destination_id'].nunique()}")
print(f"crowd_index range: [{df['crowd_index'].min():.3f} – {df['crowd_index'].max():.3f}]")
print(f"\\nTop destinations by avg pageviews:")
print(df.groupby('name')['avg_pageviews'].mean().nlargest(15).round(0).to_string())
"""),
        md("## crowd_index heatmap — seasonal variation"),
        code("""\
TOP = df.groupby('name')['avg_pageviews'].mean().nlargest(40).index
pivot = df[df['name'].isin(TOP)].pivot_table(index='name', columns='month', values='crowd_index')
pivot.columns = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
pivot = pivot.loc[pivot.max(axis=1).sort_values(ascending=False).index]

fig, ax = plt.subplots(figsize=(14, 12))
sns.heatmap(pivot, annot=True, fmt='.2f', cmap='YlOrRd', vmin=0, vmax=1,
            linewidths=0.4, ax=ax, cbar_kws={'label': 'crowd_index'})
ax.set_title('crowd_index by Month — Top 40 Destinations by Pageviews')
plt.tight_layout(); plt.show()
"""),
        md("## Absolute pageviews distribution (log scale)"),
        code("""\
import numpy as np
annual = df.groupby('name')['avg_pageviews'].mean()
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].hist(np.log10(annual[annual > 0] + 1), bins=30, edgecolor='white')
axes[0].set_xlabel('log10(avg_pageviews)'); axes[0].set_title('Log Pageviews Distribution')
axes[0].axvline(np.log10(annual.mean()), color='red', linestyle='--', label=f'mean={annual.mean():.0f}')
axes[0].legend()

axes[1].barh(annual.nlargest(15).index[::-1], annual.nlargest(15).values[::-1])
axes[1].set_xlabel('avg monthly pageviews')
axes[1].set_title('Top 15 by Pageviews')
plt.tight_layout(); plt.show()
print(f"\\nDestinations with <1000 avg monthly pageviews: {(annual < 1000).sum()}")
"""),
        md("## Best and worst months per city"),
        code("""\
best_month = df.loc[df.groupby('destination_id')['crowd_index'].idxmax()][['name','month','crowd_index']]
worst_month = df.loc[df.groupby('destination_id')['crowd_index'].idxmin()][['name','month','crowd_index']]

month_names = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
               7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
for ax, data, title in [
    (axes[0], best_month, 'Peak crowd month distribution'),
    (axes[1], worst_month, 'Quietest month distribution')
]:
    cnt = data['month'].value_counts().reindex(range(1,13), fill_value=0)
    ax.bar(month_names.values(), cnt.values)
    ax.set_title(title)
plt.tight_layout(); plt.show()
"""),
        md("## Hidden gem metric: popular destination in low season"),
        code("""\
annual_views = df.groupby(['destination_id','name'])['avg_pageviews'].mean().reset_index()
low_season = df.loc[df.groupby('destination_id')['crowd_index'].idxmin()][['destination_id','month','crowd_index']]
gems = annual_views.merge(low_season, on='destination_id')
gems['gem_score'] = np.log10(gems['avg_pageviews'] + 1) * (1 - gems['crowd_index'])
print("Top 15 'hidden gem' months (popular dest in off-season):")
print(gems.nlargest(15, 'gem_score')[['name','month','avg_pageviews','crowd_index','gem_score']].to_string(index=False))
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 7. VISA
# ════════════════════════════════════════════════════════════════════════════
save(
    "11_visa_rules.ipynb",
    [
        md("# Visa Rules — Passport Index 2025 (ilyankou/passport-index-dataset)"),
        code(SETUP),
        code("""\
df = load('visa_rules')
dests = load('destinations')[['id','name','country_code','region']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Total records: {len(df):,}")
print(f"Unique passports: {df['citizenship_code'].nunique()}")
print(f"Unique destinations: {df['destination_id'].nunique()}")
print()
print(df['visa_type'].value_counts())
"""),
        md("## Visa type distribution"),
        code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
vc = df['visa_type'].value_counts()
colors = {'visa_free':'#2ecc71','evisa':'#f39c12','visa_required':'#e74c3c','no_admission':'#7f8c8d'}
axes[0].pie(vc.values, labels=vc.index, autopct='%1.1f%%',
            colors=[colors.get(v,'gray') for v in vc.index], startangle=140)
axes[0].set_title('Global Visa Type Distribution')

vs = df['visa_score'].value_counts().sort_index()
axes[1].bar([f'{v:.1f}' for v in vs.index], vs.values,
            color=[colors.get(k,'gray') for k in ['no_admission','visa_required','evisa','visa_free']])
axes[1].set_xlabel('visa_score'); axes[1].set_title('visa_score Distribution')
plt.tight_layout(); plt.show()
"""),
        md("## Passport power ranking — top & bottom 20"),
        code("""\
passport_power = df.groupby('citizenship_code').apply(
    lambda x: (x['visa_type']=='visa_free').sum()
).sort_values(ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
top20 = passport_power.head(20)
axes[0].barh(top20.index[::-1], top20.values[::-1], color='#2ecc71')
axes[0].set_title('Top 20 strongest passports (visa-free destinations)')
axes[0].set_xlabel('# visa-free destinations')

bot20 = passport_power.tail(20)
axes[1].barh(bot20.index[::-1], bot20.values[::-1], color='#e74c3c')
axes[1].set_title('20 weakest passports')
axes[1].set_xlabel('# visa-free destinations')
plt.tight_layout(); plt.show()
"""),
        md("## Destination accessibility — which destinations are easiest to enter"),
        code("""\
access = df.groupby(['destination_id','name','region']).apply(
    lambda x: (x['visa_type']=='visa_free').sum()
).reset_index(name='visa_free_passports')

print("Most accessible destinations (most passports get visa-free):")
print(access.nlargest(15,'visa_free_passports')[['name','region','visa_free_passports']].to_string(index=False))
print()
print("Hardest to enter:")
print(access.nsmallest(10,'visa_free_passports')[['name','region','visa_free_passports']].to_string(index=False))
"""),
        md("## Visa policy by region"),
        code("""\
region_visa = df.groupby(['region','visa_type']).size().unstack(fill_value=0)
region_visa_pct = region_visa.div(region_visa.sum(axis=1), axis=0) * 100

fig, ax = plt.subplots(figsize=(12, 5))
region_visa_pct.plot.barh(stacked=True, ax=ax,
    color=[colors.get(c,'gray') for c in region_visa_pct.columns])
ax.set_xlabel('% of visa rules'); ax.set_title('Visa Type Distribution by Destination Region')
ax.legend(loc='lower right')
plt.tight_layout(); plt.show()
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 8. POI
# ════════════════════════════════════════════════════════════════════════════
save(
    "12_poi.ipynb",
    [
        md("# Points of Interest — OTM + OSM (1M+ records)"),
        code(
            SETUP
            + "\nprint('Loading POI... (1M+ rows, may take ~10s)')\ndf = load('poi')"
        ),
        code("""\
dests = load('destinations')[['id','name','country_code','region']].rename(columns={'name':'dest_name','id':'dest_id'})
df = df.merge(dests, left_on='destination_id', right_on='dest_id')
print(f"Total POI: {len(df):,}")
print(f"Sources: {df['source'].value_counts().to_dict()}")
print(f"Destinations covered: {df['destination_id'].nunique()}")
"""),
        md("## Source and category breakdown"),
        code("""\
cat_total = df['category'].value_counts()
src_cat = df.groupby(['source','category']).size().unstack(fill_value=0)
print("=== POI by category (total) ===")
print(cat_total.to_string())
print()
print("=== POI by category × source ===")
print(src_cat.T.sort_values('overpass_osm', ascending=False).to_string())

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
src_cat.T.sort_values('overpass_osm', ascending=False).plot.barh(ax=axes[0], stacked=False)
axes[0].set_title('POI count by category × source')
axes[0].set_xlabel('count')
axes[1].barh(cat_total.index[::-1], cat_total.values[::-1])
axes[1].set_title('Total POI by category')
axes[1].set_xlabel('count')
plt.tight_layout(); plt.show()
"""),
        md("## popularity_score: OTM (real ratings) vs OSM (tag-based)"),
        code("""\
for src in ['opentripmap', 'overpass_osm']:
    sub = df[df['source']==src]['popularity_score']
    print(f"--- {src} (N={len(sub):,}) ---")
    print(f"  mean={sub.mean():.3f}  median={sub.median():.3f}  std={sub.std():.3f}")
    print(f"  p10={sub.quantile(0.10):.3f}  p25={sub.quantile(0.25):.3f}  p75={sub.quantile(0.75):.3f}  p90={sub.quantile(0.90):.3f}")
    print(f"  zeros: {(sub==0).sum():,}  ones: {(sub==1).sum():,}")
    print()

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
for i, (src, color) in enumerate([('opentripmap','#4C72B0'),('overpass_osm','#DD8452')]):
    sub = df[df['source']==src]['popularity_score']
    axes[i].hist(sub, bins=30, edgecolor='white', color=color)
    axes[i].set_title(f'{src}\\nN={len(sub):,}  avg={sub.mean():.3f}  median={sub.median():.3f}')
    axes[i].set_xlabel('popularity_score')
plt.suptitle('popularity_score Distribution by Source')
plt.tight_layout(); plt.show()
"""),
        md("## Top / bottom destinations by POI count"),
        code("""\
poi_per_dest = df.groupby('dest_name').size().sort_values(ascending=False)
print(f"Total destinations with POI: {len(poi_per_dest)}")
print(f"Median POI per dest: {poi_per_dest.median():.0f}  |  Mean: {poi_per_dest.mean():.0f}")
print(f"Destinations with <50 POI: {(poi_per_dest < 50).sum()}")
print(f"Destinations with >5000 POI: {(poi_per_dest > 5000).sum()}")
print()
print("=== TOP 20 by POI count ===")
print(poi_per_dest.head(20).to_string())
print()
print("=== BOTTOM 20 ===")
print(poi_per_dest.tail(20).to_string())

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
poi_per_dest.head(20).plot.barh(ax=axes[0], color='steelblue')
axes[0].invert_yaxis()
axes[0].set_title('Top 20 destinations by POI count')
axes[0].set_xlabel('POI count')
poi_per_dest.tail(20).plot.barh(ax=axes[1], color='salmon')
axes[1].invert_yaxis()
axes[1].set_title('Bottom 20 (fewest POI)')
axes[1].set_xlabel('POI count')
plt.tight_layout(); plt.show()
"""),
        md("## OTM ratings distribution"),
        code("""\
rated = df[df['rating'].notna()]
print(f"OTM POI with ratings: {len(rated):,}  ({100*len(rated)/len(df):.1f}% of total)")
print(f"Rating mean={rated['rating'].mean():.2f}  median={rated['rating'].median():.2f}  std={rated['rating'].std():.2f}")
print()
print("=== Avg rating by category (OTM) ===")
print(rated.groupby('category')['rating'].agg(['mean','count']).round(2).sort_values('mean', ascending=False).to_string())

fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(rated['rating'], bins=20, edgecolor='white', color='steelblue')
ax.set_xlabel('rating (0–10)'); ax.set_title('OTM Rating Distribution')
ax.axvline(rated['rating'].mean(), color='red', linestyle='--',
           label=f'mean={rated["rating"].mean():.2f}')
ax.legend()
plt.tight_layout(); plt.show()
"""),
        md("## Coordinate quality check"),
        code("""\
center_coords = df.groupby('destination_id').apply(
    lambda g: ((g['lat'] == g['lat'].iloc[0]) & (g['lng'] == g['lng'].iloc[0])).sum()
).sort_values(ascending=False)
at_center = (center_coords > 0).sum()
print(f"Destinations with POI stacked at same coordinate: {at_center}")
print()

# POI with null coordinates
null_coords = df[df['lat'].isna() | df['lng'].isna()]
print(f"POI with null coordinates: {len(null_coords):,}")

# Check top destinations for stacked coordinates
print()
print("=== Top 10 stacking by destination (POI at identical coords) ===")
print(center_coords.head(10).to_string())
"""),
    ],
)

# ════════════════════════════════════════════════════════════════════════════
# 9. TRAJECTORIES
# ════════════════════════════════════════════════════════════════════════════
save(
    "13_trajectories.ipynb",
    [
        md("# Trajectories — Itinerary Templates per Destination"),
        code(SETUP),
        code("""\
import ast
df = load('trajectories')
dests = load('destinations')[['id','name','country_code','region']]
df = df.merge(dests, left_on='destination_id', right_on='id')
print(f"Total trajectories: {len(df)}")
print(f"Destinations covered: {df['destination_id'].nunique()}")
print()
print(df['duration_days'].value_counts().sort_index().to_string())
"""),
        md("## Activity tags distribution"),
        code("""\
from collections import Counter

all_tags = []
for tags in df['activity_tags'].dropna():
    try:
        parsed = ast.literal_eval(tags) if isinstance(tags, str) else tags
        all_tags.extend(parsed if isinstance(parsed, list) else [])
    except Exception:
        pass

tag_counts = Counter(all_tags)
fig, ax = plt.subplots(figsize=(10, 5))
tags_series = pd.Series(dict(tag_counts.most_common(20)))
tags_series[::-1].plot.barh(ax=ax)
ax.set_title('Activity Tags in Trajectories')
ax.set_xlabel('count')
plt.tight_layout(); plt.show()
print("Total tag occurrences:", sum(tag_counts.values()))
"""),
        md("## POI per trajectory (sequence length)"),
        code("""\
import ast

def seq_len(s):
    try:
        parsed = ast.literal_eval(s) if isinstance(s, str) else s
        return len(parsed) if isinstance(parsed, list) else 0
    except Exception:
        return 0

df['poi_count'] = df['sequence_of_poi'].apply(seq_len)

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
for i, days in enumerate([3, 5, 7]):
    sub = df[df['duration_days']==days]['poi_count']
    axes[i % 2].hist(sub, bins=20, alpha=0.7, label=f'{days}-day', edgecolor='white')

axes[0].set_title('POI count per 3 and 5-day trajectories')
axes[0].set_xlabel('# POI in sequence')
axes[0].legend()

sub7 = df[df['duration_days']==7]['poi_count']
axes[1].hist(sub7, bins=20, color='C2', edgecolor='white', label='7-day')
axes[1].set_title('POI count per 7-day trajectories')
axes[1].set_xlabel('# POI in sequence')
axes[1].legend()
plt.tight_layout(); plt.show()

print(df.groupby('duration_days')['poi_count'].describe().round(1).to_string())
"""),
        md("## Sample trajectories"),
        code("""\
import ast

def fmt_seq(s, n=5):
    try:
        parsed = ast.literal_eval(s) if isinstance(s, str) else s
        return parsed[:n] if isinstance(parsed, list) else []
    except Exception:
        return []

sample = df[df['name'].isin(['Paris','Bangkok','Tokyo','Reykjavik'])].copy()
for _, row in sample.iterrows():
    seq = fmt_seq(row['sequence_of_poi'])
    tags = row['activity_tags']
    print(f"{row['name']} ({row['duration_days']}d) tags={tags}")
    print(f"  first POI IDs: {seq[:4]}")
    print()
"""),
    ],
)

print("All notebooks generated.")
