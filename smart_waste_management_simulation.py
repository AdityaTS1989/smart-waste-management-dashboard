import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.facecolor':'#0B0F0B','axes.facecolor':'#131813',
    'axes.edgecolor':'#1E2E1E','axes.labelcolor':'#C8DCC8',
    'xtick.color':'#5A7A5A','ytick.color':'#5A7A5A',
    'grid.color':'#1E2E1E','grid.alpha':0.6,'text.color':'#E0EDE0',
    'font.family':'DejaVu Sans','axes.titlepad':14,
    'axes.titlesize':12,'axes.titleweight':'bold',
})
GREEN,YELLOW,ORANGE,RED,BLUE,TEAL = '#4ADE80','#FACC15','#FB923C','#F87171','#60A5FA','#2DD4BF'

np.random.seed(42)

# ── 10 SMART BINS across a city / campus ─────────────────────
bins_info = {
    'BIN-01': {'zone':'Market Area',    'capacity_L':120, 'fill_rate':5.5},
    'BIN-02': {'zone':'Market Area',    'capacity_L':120, 'fill_rate':6.5},
    'BIN-03': {'zone':'Residential A',  'capacity_L':80,  'fill_rate':3.0},
    'BIN-04': {'zone':'Residential B',  'capacity_L':80,  'fill_rate':3.5},
    'BIN-05': {'zone':'College Campus', 'capacity_L':100, 'fill_rate':4.5},
    'BIN-06': {'zone':'College Campus', 'capacity_L':100, 'fill_rate':8.0},
    'BIN-07': {'zone':'Bus Stand',      'capacity_L':150, 'fill_rate':8.0},
    'BIN-08': {'zone':'Bus Stand',      'capacity_L':150, 'fill_rate':7.5},
    'BIN-09': {'zone':'Park',           'capacity_L':60,  'fill_rate':2.0},
    'BIN-10': {'zone':'Park',           'capacity_L':60,  'fill_rate':2.5},
}

# Simulate 7 days of readings every 2 hours
timestamps = pd.date_range('2024-06-01', periods=7*12, freq='2h')
n = len(timestamps)
hours = timestamps.hour.to_numpy()

rows = []
for bin_id, info in bins_info.items():
    level = 5.0  # starts nearly empty
    for ts in timestamps:
        h = ts.hour
        # Fill faster during busy hours (8am-10pm)
        busy = 1.5 if 8 <= h <= 22 else 0.4
        # Weekend market bins fill faster
        weekend = 1.3 if ts.dayofweek >= 5 and 'Market' in info['zone'] else 1.0
        # Random noise
        fill_inc = info['fill_rate'] * busy * weekend * np.random.uniform(0.6, 1.4) / 6
        level = min(100, level + fill_inc)

        # Collection event: empty bin when it hits 90%+
        collected = False
        if level >= 85:
            level = np.random.uniform(2, 8)
            collected = True

        rows.append({
            'timestamp': ts,
            'bin_id': bin_id,
            'zone': info['zone'],
            'capacity_L': info['capacity_L'],
            'fill_level_pct': round(level, 1),
            'collected': int(collected),
            'hour': ts.hour,
            'date': ts.date(),
            'day_name': ts.strftime('%a'),
        })

df = pd.DataFrame(rows)

# ── ALERT THRESHOLDS ──────────────────────────────────────────
df['status'] = pd.cut(df['fill_level_pct'],
                      bins=[0,40,70,90,100],
                      labels=['🟢 Low','🟡 Medium','🟠 High','🔴 Full'],
                      right=True)
df['alert_high']    = (df['fill_level_pct'] >= 70).astype(int)
df['alert_full']    = (df['fill_level_pct'] >= 90).astype(int)
df['needs_pickup']  = (df['fill_level_pct'] >= 75).astype(int)

df.to_csv('waste_bin_data.csv', index=False)
print(f"✅ Generated {len(df):,} readings | {df['bin_id'].nunique()} bins | 7 days")
print(f"🚛 Total collections: {df['collected'].sum()}")
print(f"⚠️  High-fill alerts : {df['alert_high'].sum()}")
print(f"🔴 Full-bin alerts  : {df['alert_full'].sum()}")

# ── CHART 1 — MAIN DASHBOARD ──────────────────────────────────
fig = plt.figure(figsize=(16, 12))
fig.patch.set_facecolor('#0B0F0B')
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.32)

# Fill level trend for all bins (sample: first 3 days)
ax1 = fig.add_subplot(gs[0, :]); ax1.set_facecolor('#131813')
sample = df[df['timestamp'] < pd.Timestamp('2024-06-04')]
colors_bin = [GREEN, BLUE, YELLOW, ORANGE, RED, TEAL,'#C084FC','#FB7185','#A3E635','#F9A8D4']
for i, (bid, grp) in enumerate(sample.groupby('bin_id')):
    ax1.plot(grp['timestamp'], grp['fill_level_pct'],
             linewidth=1.6, label=f"{bid} ({grp['zone'].iloc[0]})",
             color=colors_bin[i], alpha=0.85)
ax1.axhline(y=90, color=RED, linestyle='--', linewidth=1.3, alpha=0.6, label='Full Threshold (90%)')
ax1.axhline(y=70, color=ORANGE, linestyle=':', linewidth=1.1, alpha=0.5, label='High Alert (70%)')
ax1.set_title('📈  Bin Fill Level Trends — All 10 Bins (First 3 Days)', color='#E0EDE0', fontsize=13)
ax1.set_ylabel('Fill Level (%)'); ax1.set_ylim(0, 105)
ax1.legend(framealpha=0.12, labelcolor='white', fontsize=7, ncol=4, loc='upper right')
ax1.grid(True, alpha=0.25)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.tick_params(axis='x', rotation=20)

# Current fill level gauge bar chart (latest reading per bin)
latest = df.groupby('bin_id').last().reset_index()
ax2 = fig.add_subplot(gs[1, 0]); ax2.set_facecolor('#131813')
bar_colors = []
for v in latest['fill_level_pct']:
    if v < 40: bar_colors.append(GREEN)
    elif v < 70: bar_colors.append(YELLOW)
    elif v < 90: bar_colors.append(ORANGE)
    else: bar_colors.append(RED)
bars = ax2.barh(latest['bin_id'], latest['fill_level_pct'],
                color=bar_colors, alpha=0.85, edgecolor='none')
ax2.axvline(x=90, color=RED, linestyle='--', linewidth=1.2, alpha=0.6, label='Full (90%)')
ax2.axvline(x=70, color=ORANGE, linestyle=':', linewidth=1.1, alpha=0.5, label='High (70%)')
ax2.set_title('📊  Current Fill Level — All Bins (Latest)')
ax2.set_xlabel('Fill Level (%)')
ax2.set_xlim(0, 110)
ax2.legend(framealpha=0.15, labelcolor='white', fontsize=8)
ax2.grid(True, axis='x', alpha=0.25)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
for bar, val, bid in zip(bars, latest['fill_level_pct'], latest['bin_id']):
    ax2.text(val+1, bar.get_y()+bar.get_height()/2,
             f'{val:.0f}%', va='center', color='#E0EDE0', fontsize=9)

# Collections by zone
zone_cols = df[df['collected']==1].groupby('zone').size().sort_values(ascending=True)
ax3 = fig.add_subplot(gs[1, 1]); ax3.set_facecolor('#131813')
bars3 = ax3.barh(zone_cols.index, zone_cols.values,
                 color=[BLUE,GREEN,TEAL,ORANGE,RED][:len(zone_cols)], alpha=0.85, edgecolor='none')
ax3.set_title('🚛  Total Collections by Zone (7 Days)')
ax3.set_xlabel('Number of Collections')
ax3.grid(True, axis='x', alpha=0.25)
ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)
for bar, val in zip(bars3, zone_cols.values):
    ax3.text(val+0.1, bar.get_y()+bar.get_height()/2,
             str(val), va='center', color='#E0EDE0', fontsize=10)

fig.suptitle('🗑️  Smart Waste Management — 7-Day Monitoring Dashboard',
             fontsize=15, color='#E0EDE0', y=1.01)
plt.savefig('chart1_waste_dashboard.png', dpi=150, bbox_inches='tight', facecolor='#0B0F0B')
plt.close(); print("Saved chart1")

# ── CHART 2 — HOURLY HEATMAP (fill level avg by bin & hour) ──
pivot = df.pivot_table(values='fill_level_pct', index='bin_id', columns='hour', aggfunc='mean')
fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(pivot, annot=True, fmt='.0f', cmap='RdYlGn_r',
            linewidths=0.3, linecolor='#0B0F0B',
            cbar_kws={'label':'Avg Fill Level (%)'}, ax=ax,
            vmin=0, vmax=100)
ax.set_title('🕐  Avg Fill Level by Bin & Hour of Day — Identifies Busy Collection Times',
             fontsize=12, pad=12)
ax.set_xlabel('Hour of Day'); ax.set_ylabel('Bin ID')
plt.tight_layout()
plt.savefig('chart2_hourly_heatmap.png', dpi=150, bbox_inches='tight', facecolor='#0B0F0B')
plt.close(); print("Saved chart2")

# ── CHART 3 — DAILY COLLECTIONS + FILL STATUS PIE ────────────
daily_cols = df[df['collected']==1].groupby('date').size().reset_index(name='collections')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.bar(range(len(daily_cols)), daily_cols['collections'],
        color=[GREEN if v<=5 else ORANGE if v<=8 else RED for v in daily_cols['collections']],
        alpha=0.85, edgecolor='none')
ax1.set_title('🚛  Daily Collection Count (7 Days)')
ax1.set_xlabel('Day'); ax1.set_ylabel('Number of Collections')
ax1.set_xticks(range(len(daily_cols)))
ax1.set_xticklabels([str(d)[5:] for d in daily_cols['date']], rotation=20)
ax1.axhline(y=daily_cols['collections'].mean(), color=YELLOW, linestyle='--',
            linewidth=1.3, alpha=0.7, label=f"Avg: {daily_cols['collections'].mean():.1f}/day")
ax1.legend(framealpha=0.15, labelcolor='white', fontsize=9)
ax1.grid(True, axis='y', alpha=0.25)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
for i, v in enumerate(daily_cols['collections']):
    ax1.text(i, v+0.1, str(v), ha='center', color='#E0EDE0', fontsize=10)

# Overall fill status distribution
status_counts = df['status'].value_counts()
label_clean = [str(s) for s in status_counts.index]
pie_colors = [GREEN, YELLOW, ORANGE, RED][:len(status_counts)]
wedges, texts, autotexts = ax2.pie(
    status_counts.values, labels=label_clean, autopct='%1.1f%%',
    colors=pie_colors, startangle=90,
    wedgeprops=dict(width=0.55, edgecolor='#0B0F0B', linewidth=2),
    textprops={'color':'#E0EDE0','fontsize':9}, pctdistance=0.78)
for at in autotexts: at.set_color('#0B0F0B'); at.set_fontweight('bold')
ax2.set_title('🥧  Overall Fill Status Distribution')
plt.tight_layout()
plt.savefig('chart3_collections_status.png', dpi=150, bbox_inches='tight', facecolor='#0B0F0B')
plt.close(); print("Saved chart3")

# ── CHART 4 — ZONE COMPARISON + ROUTE PRIORITY ───────────────
zone_summary = df.groupby('zone').agg(
    avg_fill=('fill_level_pct','mean'),
    max_fill=('fill_level_pct','max'),
    total_collections=('collected','sum'),
    alerts=('alert_high','sum'),
).reset_index().sort_values('avg_fill', ascending=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

x = np.arange(len(zone_summary)); w = 0.35
ax1.bar(x-w/2, zone_summary['avg_fill'], w, label='Avg Fill %', color=BLUE, alpha=0.85, edgecolor='none')
ax1.bar(x+w/2, zone_summary['max_fill'], w, label='Max Fill %', color=RED, alpha=0.75, edgecolor='none')
ax1.set_xticks(x); ax1.set_xticklabels(zone_summary['zone'], rotation=18, ha='right')
ax1.set_title('📍  Avg vs Max Fill Level by Zone')
ax1.set_ylabel('Fill Level (%)'); ax1.set_ylim(0, 115)
ax1.legend(framealpha=0.15, labelcolor='white', fontsize=9)
ax1.grid(True, axis='y', alpha=0.25)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.axhline(y=90, color=RED, linestyle='--', linewidth=1, alpha=0.5)

# Route priority: bins that need pickup right now
priority = df.groupby('bin_id').last().reset_index()
priority = priority.sort_values('fill_level_pct', ascending=False)
route_colors = [RED if v>=90 else ORANGE if v>=70 else YELLOW if v>=40 else GREEN
                for v in priority['fill_level_pct']]
bars_p = ax2.bar(priority['bin_id'], priority['fill_level_pct'],
                 color=route_colors, alpha=0.85, edgecolor='none')
ax2.axhline(y=90, color=RED, linestyle='--', linewidth=1.2, alpha=0.6, label='Collect Now (90%)')
ax2.axhline(y=70, color=ORANGE, linestyle=':', linewidth=1, alpha=0.5, label='Urgent (70%)')
ax2.set_title('🚛  Collection Route Priority\n(Current Fill Level — Highest First)')
ax2.set_ylabel('Fill Level (%)')
ax2.tick_params(axis='x', rotation=20)
ax2.legend(framealpha=0.15, labelcolor='white', fontsize=8)
ax2.grid(True, axis='y', alpha=0.25)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
for bar, val in zip(bars_p, priority['fill_level_pct']):
    ax2.text(bar.get_x()+bar.get_width()/2, val+1, f'{val:.0f}%',
             ha='center', color='#E0EDE0', fontsize=8)

plt.tight_layout()
plt.savefig('chart4_zone_priority.png', dpi=150, bbox_inches='tight', facecolor='#0B0F0B')
plt.close(); print("Saved chart4")

# ── LIVE MONITORING TABLE ─────────────────────────────────────
print("\n" + "="*72)
print("  LIVE BIN STATUS — CURRENT READINGS (ALL 10 BINS)")
print("="*72)
print(f"{'Bin':>6} {'Zone':<18} {'Fill%':>6} {'Status':<16} {'Action'}")
print("-"*72)
for _, row in latest.sort_values('fill_level_pct', ascending=False).iterrows():
    v = row['fill_level_pct']
    if v >= 90:   status_str, action = "🔴 FULL",   "🚛 COLLECT IMMEDIATELY"
    elif v >= 70: status_str, action = "🟠 HIGH",   "⚠️  SCHEDULE PICKUP"
    elif v >= 40: status_str, action = "🟡 MEDIUM", "📋 MONITOR"
    else:         status_str, action = "🟢 LOW",    "✅ OK"
    print(f"{row['bin_id']:>6} {row['zone']:<18} {v:>5.1f}%  {status_str:<16} {action}")
print("="*72)

# ── FINAL REPORT ──────────────────────────────────────────────
bins_needing_pickup = int((latest['fill_level_pct'] >= 75).sum())
total_collections   = int(df['collected'].sum())
bcol = df[df['collected']==1].groupby('zone').size(); busiest_zone = bcol.idxmax() if len(bcol)>0 else 'N/A'
busiest_bin  = df.groupby('bin_id')['collected'].sum().idxmax()

print()
print("╔══════════════════════════════════════════════════════╗")
print("║   SMART WASTE MANAGEMENT — FINAL REPORT             ║")
print("╠══════════════════════════════════════════════════════╣")
print(f"║  🗑️  Total Bins        : 10 across 5 zones           ║")
print(f"║  📅 Monitoring Period : 7 Days (840 readings)       ║")
print(f"║  🚛 Total Collections : {total_collections:<28}║")
print(f"║  ⚠️  High-Fill Alerts  : {int(df['alert_high'].sum()):<28}║")
print(f"║  🔴 Full-Bin Alerts   : {int(df['alert_full'].sum()):<28}║")
print("╠══════════════════════════════════════════════════════╣")
print(f"║  🏆 Busiest Zone      : {busiest_zone:<28}║")
print(f"║  🏆 Most Collected Bin: {busiest_bin:<28}║")
print(f"║  🚨 Bins Need Pickup  : {bins_needing_pickup} bins right now{'':<16}║")
print("╠══════════════════════════════════════════════════════╣")
print("║  📁 Files Saved:                                     ║")
print("║     waste_bin_data.csv                              ║")
print("║     chart1_waste_dashboard.png                      ║")
print("║     chart2_hourly_heatmap.png                       ║")
print("║     chart3_collections_status.png                   ║")
print("║     chart4_zone_priority.png                        ║")
print("╚══════════════════════════════════════════════════════╝")
