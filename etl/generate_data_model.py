import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(22, 16))
ax.set_xlim(0, 22)
ax.set_ylim(0, 16)
ax.axis('off')
fig.patch.set_facecolor('#F8F9FA')

# Colour palette
C_RAW           = '#DBEAFE'
C_BRIDGE        = '#EDE9FE'
C_DEMAND        = '#DCFCE7'
C_OUTPUT        = '#FEF3C7'
C_BORDER_RAW    = '#3B82F6'
C_BORDER_BRIDGE = '#7C3AED'
C_BORDER_DEMAND = '#16A34A'
C_BORDER_OUTPUT = '#D97706'
C_ARROW         = '#64748B'


def draw_table(ax, x, y, w, h, title, fields, color, border_color):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle='round,pad=0.05',
        facecolor=color, edgecolor=border_color, linewidth=1.8, zorder=3
    )
    ax.add_patch(box)

    title_h = 0.42
    title_box = FancyBboxPatch(
        (x, y + h - title_h), w, title_h,
        boxstyle='round,pad=0.04',
        facecolor=border_color, edgecolor=border_color, linewidth=0, zorder=4
    )
    ax.add_patch(title_box)
    ax.text(x + w / 2, y + h - title_h / 2, title,
            ha='center', va='center',
            fontsize=7.5, fontweight='bold', color='white', zorder=5)

    row_h = (h - title_h - 0.1) / max(len(fields), 1)
    for i, field in enumerate(fields):
        fy = y + h - title_h - 0.1 - (i + 0.5) * row_h
        style = dict(fontsize=6.2, va='center', zorder=5)
        if '(PK)' in field:
            ax.text(x + 0.12, fy, field, ha='left',
                    color='#1D4ED8', fontweight='bold', **style)
        elif '(FK)' in field:
            ax.text(x + 0.12, fy, field, ha='left',
                    color='#7C3AED', **style)
        else:
            ax.text(x + 0.12, fy, field, ha='left',
                    color='#374151', **style)


def arrow(ax, x1, y1, x2, y2, label='', color=C_ARROW, lw=1.4, rad=0.0):
    style = 'arc3,rad={}'.format(rad)
    ax.annotate(
        '', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                        connectionstyle=style),
        zorder=6
    )
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        ax.text(mx, my + 0.14, label,
                ha='center', fontsize=5.5, color=color, style='italic', zorder=7,
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='none', alpha=0.85))


# Layer labels
layer_info = [
    (13.6, 'LAYER 1 — RAW MATERIAL',               '#3B82F6'),
    (9.4,  'LAYER 2 — PRODUCTION BRIDGE (RT* to FT*)', '#7C3AED'),
    (5.6,  'LAYER 3 — DEMAND',                     '#16A34A'),
    (1.2,  'LAYER 4 — OUTPUTS',                    '#D97706'),
]
for y_pos, label, col in layer_info:
    ax.text(0.3, y_pos, label, fontsize=7, color=col,
            fontweight='bold', style='italic', va='center', alpha=0.7)
    ax.axhline(y=y_pos - 0.25, xmin=0.01, xmax=0.99,
               color=col, lw=0.5, alpha=0.2, linestyle='--')

# Tables
draw_table(ax, 0.4, 10.2, 3.6, 3.1, 'planning_inventory',
    ['ItemNo (PK)', 'Location (PK)', 'WorkDate (PK)',
     'Quantity', 'Shipment Date', 'Order No.'],
    C_RAW, C_BORDER_RAW)

draw_table(ax, 5.0, 10.2, 3.8, 3.1, 'cm_inbound',
    ['PO Number (PK)', 'Item No. RT (FK)', 'Location (FK)',
     'Vendor', 'Commodity', 'Expected Qty', 'Received Qty',
     'Delivery Date', 'Status'],
    C_RAW, C_BORDER_RAW)

draw_table(ax, 9.8, 10.2, 3.6, 3.1, 'planning_purchases',
    ['Document No. (PK)', 'Item No. RT (FK)', 'Location Code (FK)',
     'Vendor Name', 'Expected Receipt Date', 'Quantity'],
    C_RAW, C_BORDER_RAW)

draw_table(ax, 14.5, 10.2, 3.6, 3.1, 'planning_transfers',
    ['Document No. (PK)', 'Item No. RT (FK)',
     'Transfer-from (FK)', 'Transfer-to (FK)',
     'Ready Date', 'Qty Shipped', 'Qty In Transit', 'Qty Received'],
    C_RAW, C_BORDER_RAW)

draw_table(ax, 7.5, 6.5, 4.0, 2.6, 'planning_production  (RT to FT)',
    ['Prod. Order No. (PK)', 'Item No. FT (FK)', 'Location Code (FK)',
     'Ending Date', 'Planned Qty', 'Remaining Qty',
     'Finished Qty', 'Production Reason'],
    C_BRIDGE, C_BORDER_BRIDGE)

draw_table(ax, 1.0, 2.8, 3.8, 2.6, 'planning_sales',
    ['Document No. (PK)', 'Item No. FT (FK)', 'Location Code (FK)',
     'Customer Name', 'Outstanding Qty', 'Ready Date',
     'Customer Sales Type'],
    C_DEMAND, C_BORDER_DEMAND)

draw_table(ax, 5.6, 2.8, 4.2, 2.6, 'sales',
    ['Source ID (PK)', 'Item No. FT (FK)', 'Shipping Location (FK)',
     'Destination Name', 'Original Qty', 'Outstanding Qty',
     'Unit Price', 'Allocation Flag'],
    C_DEMAND, C_BORDER_DEMAND)

draw_table(ax, 11.5, 2.8, 4.0, 2.6, 'net_available_inventory',
    ['ItemNo (PK)', 'Location (PK)', 'Date (PK)',
     '= Inventory + Inbound',
     '+ Transfers In - Out',
     '+ Packed Output - Demand',
     'NetAvailable'],
    C_OUTPUT, C_BORDER_OUTPUT)

draw_table(ax, 16.2, 6.5, 3.5, 2.0, 'shortage_alerts',
    ['ItemNo (PK)', 'Location (PK)', 'Date (PK)',
     'Gap (cases)', 'Severity'],
    C_OUTPUT, C_BORDER_OUTPUT)

draw_table(ax, 16.2, 2.8, 3.5, 2.6, 'pack_schedule',
    ['ItemNo FT (PK)', 'Location (PK)', 'Pack Date (PK)',
     'Suggested Qty', 'Feasible Qty',
     'Raw Lbs Required', 'Raw Constrained'],
    C_OUTPUT, C_BORDER_OUTPUT)

# Arrows — Layer 1 joins
arrow(ax, 4.0, 11.7, 5.0, 11.7, 'ItemNo + Location')
arrow(ax, 4.0, 11.3, 9.8, 11.3, 'ItemNo + LocationCode')
arrow(ax, 4.0, 11.0, 14.5, 11.0, 'ItemNo + Location', rad=-0.08)

# planning_inventory to production (bridge)
arrow(ax, 2.2, 10.2, 8.8, 9.1,
      'Location (raw consumed)',
      color=C_BORDER_BRIDGE, lw=1.6, rad=0.15)

# production to demand tables
arrow(ax, 8.5, 6.5, 4.2, 5.4,
      'ItemNo_FT + LocationCode',
      color=C_BORDER_BRIDGE, lw=1.6)
arrow(ax, 9.5, 6.5, 7.5, 5.4,
      'ItemNo_FT + ShippingLocation',
      color=C_BORDER_BRIDGE, lw=1.6)

# planning_sales to sales (DocumentNo = SourceID)
arrow(ax, 4.8, 4.1, 5.6, 4.1,
      'DocumentNo = SourceID',
      color='#DC2626', lw=1.5)

# All tables into net_available
arrow(ax, 2.2, 2.8, 12.5, 3.8, color=C_BORDER_OUTPUT, lw=1.2, rad=-0.2)
arrow(ax, 7.7, 2.8, 12.5, 3.6, color=C_BORDER_OUTPUT, lw=1.2, rad=-0.1)
arrow(ax, 5.0, 11.0, 12.5, 4.2, color=C_BORDER_OUTPUT, lw=1.0, rad=0.25)
arrow(ax, 9.8, 10.5, 13.0, 4.2, color=C_BORDER_OUTPUT, lw=1.0, rad=0.2)
arrow(ax, 14.5, 10.5, 13.5, 4.2, color=C_BORDER_OUTPUT, lw=1.0, rad=0.15)

# net_available to outputs
arrow(ax, 15.5, 4.1, 16.2, 7.0, color=C_BORDER_OUTPUT, lw=1.6)
arrow(ax, 15.5, 3.8, 16.2, 3.8, color=C_BORDER_OUTPUT, lw=1.6)

# Legend
legend_items = [
    mpatches.Patch(facecolor=C_RAW,    edgecolor=C_BORDER_RAW,
                   label='Raw Material (RT*)'),
    mpatches.Patch(facecolor=C_BRIDGE, edgecolor=C_BORDER_BRIDGE,
                   label='Production Bridge'),
    mpatches.Patch(facecolor=C_DEMAND, edgecolor=C_BORDER_DEMAND,
                   label='Demand / Sales (FT*)'),
    mpatches.Patch(facecolor=C_OUTPUT, edgecolor=C_BORDER_OUTPUT,
                   label='Derived Output'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=7, framealpha=0.9,
          bbox_to_anchor=(0.01, 0.01), ncol=4)

# Title
ax.text(11, 15.6, 'Category Manager Control Tower — Data Model',
        ha='center', va='center', fontsize=13, fontweight='bold', color='#1E293B')
ax.text(11, 15.2,
        'How source tables connect to generate Shortage Alerts and Pack Schedule',
        ha='center', va='center', fontsize=8, color='#64748B')

plt.tight_layout()
plt.savefig('docs/data_model.png', dpi=160, bbox_inches='tight',
            facecolor='#F8F9FA', edgecolor='none')
print('Saved: docs/data_model.png')
