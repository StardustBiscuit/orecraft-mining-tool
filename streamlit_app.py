import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Orecraft Rekentool",
    page_icon="⚒️",
    layout="wide"
)

st.title("⚒️ Orecraft Crafting & Resource Calculator")
st.caption("Geoptimaliseerde calculator met interactief voorraadbeheer en dynamische hiërarchische doorrekening.")

# ---------------------------------------------------------
# DATABASE DATA & STRICT TIER ORDERING
# ---------------------------------------------------------
ITEMS_ORDER = [
    "Crude boots", "Crude axe", "Battle axe", "Mithril axe", "Saronite plate",
    "Saronite boots", "Saronite Gloves", "Siege gloves", "Siege boots", "Siege plate",
    "Solar shield", "Moon axe", "Assault gloves", "Assault boots", "Assault shield",
    "Eternal gloves", "Eternal plate", "Eternal greaves", "Eclipse shield", "Eclipse axe",
    "Blackrock hammer", "Lunarite gloves", "Eclipse hammer", "Eclipse plate",
    "Savage gloves", "Savage shield", "Savage boots"
]

BARS_ORDER = [
    "Copper Bar", "Iron Bar", "Mithril Bar", "Saronite Bar", "Gold Bar",
    "Cobalt Bar", "Thorium Bar", "Solar Bar", "Moonbar", "Obsidium Bar",
    "Magnetite Bar", "Sinvyr Bar", "Platinum Bar", "Blackrock Bar", "Lunarite Bar",
    "Leystone Bar", "Stardust Bar", "Aurorite Bar", "Empyrium Bar"
]

ORES_ORDER = [
    "Copper Ore", "Iron Ore", "Mithril Ore", "Saronite Ore", "Gold Ore",
    "Cobalt Ore", "Thorium Ore", "Leynir Ore", "Obsidium Ore", "Magnetite Ore",
    "Sinvyr Ore", "Platinum Ore", "Blackrock Ore", "Lunarite Ore", "Leystone Ore",
    "Stardust Ore", "Aurorite Ore", "Empyrium Ore"
]

ITEMS_DB = {
    "Crude boots": "2x Copper Bar",
    "Crude axe": "2x Iron Bar",
    "Battle axe": "1x Crude axe + 4x Copper Bar",
    "Mithril axe": "1x Battle axe + 2x Mithril Bar",
    "Saronite plate": "6x Saronite Bar",
    "Saronite boots": "4x Crude boots + 4x Gold Bar + 4x Saronite Bar",
    "Saronite Gloves": "1x Saronite plate + 2x Cobalt Bar",
    "Siege gloves": "1x Saronite Gloves + 2x Thorium Bar + 40x Iron Bar",
    "Siege boots": "2x Saronite boots + 2x Thorium Bar + 4x Cobalt Bar",
    "Siege plate": "2x Saronite plate + 2x Saronite boots + 10x Thorium Bar",
    "Solar shield": "1x Siege gloves + 2x Saronite Gloves + 2x Solar Bar",
    "Moon axe": "12x Battle axe + 8x Moonbar",
    "Assault gloves": "1x Siege gloves + 2x Saronite plate + 2x Obsidium Bar",
    "Assault boots": "2x Siege boots + 2x Magnetite Bar",
    "Assault shield": "1x Assault gloves + 1x Solar shield + 8x Obsidium Bar",
    "Eternal gloves": "6x Sinvyr Bar + 2x Solar shield",
    "Eternal plate": "30x Obsidium Bar + 60x Gold Bar + 20x Magnetite Bar",
    "Eternal greaves": "8x Saronite Gloves + 1x Assault boots",
    "Eclipse shield": "60x Moonbar + 8x Platinum Bar",
    "Eclipse axe": "200x Solar Bar + 80x Mithril axe",
    "Blackrock hammer": "8x Blackrock Bar + 1x Moon axe",
    "Lunarite gloves": "2x Lunarite Bar + 1x Eternal gloves",
    "Eclipse hammer": "60x Gold Bar + 1x Eclipse axe",
    "Eclipse plate": "1x Eclipse shield + 1x Eternal greaves + 10x Siege plate",
    "Savage gloves": "1x Lunarite gloves + 120x Sinvyr Bar",
    "Savage shield": "120x Leystone Bar + 20x Stardust Bar",
    "Savage boots": "1x Savage gloves + 24x Assault boots"
}

BARS_DB = {
    "Copper Bar": "400x Copper Ore",
    "Iron Bar": "400x Iron Ore",
    "Mithril Bar": "400x Mithril Ore",
    "Saronite Bar": "400x Saronite Ore",
    "Gold Bar": "400x Gold Ore",
    "Cobalt Bar": "400x Cobalt Ore",
    "Thorium Bar": "1200x Thorium Ore",
    "Solar Bar": "6x Cobalt Bar + 12x Copper Bar",
    "Moonbar": "12x Mithril Bar + 12x Iron Bar",
    "Obsidium Bar": "1200x Obsidium Ore + 1x Thorium Bar",
    "Magnetite Bar": "1200x Magnetite Ore + 200000x Copper Ore + 1x Solar Bar",
    "Sinvyr Bar": "1200x Sinvyr Ore + 100000x Iron Ore + 1x Moonbar",
    "Platinum Bar": "400x Platinum Ore + 1x Obsidium Bar",
    "Blackrock Bar": "400x Blackrock Ore + 1x Magnetite Bar",
    "Lunarite Bar": "400x Lunarite Ore + 1x Sinvyr Bar",
    "Leystone Bar": "400x Leystone Ore + 1x Platinum Bar",
    "Stardust Bar": "400x Stardust Ore + 1x Blackrock Bar",
    "Aurorite Bar": "400x Aurorite Ore + 1x Lunarite Bar",
    "Empyrium Bar": "400x Empyrium Ore + 1x Leystone Bar"
}

ORES_DB = {
    "Copper Ore": "Common", "Iron Ore": "Common", "Mithril Ore": "Common",
    "Saronite Ore": "Common", "Gold Ore": "Common", "Cobalt Ore": "Common",
    "Thorium Ore": "Rare", "Leynir Ore": "Rare", "Obsidium Ore": "Rare",
    "Magnetite Ore": "Rare", "Sinvyr Ore": "Precious", "Platinum Ore": "Precious",
    "Blackrock Ore": "Precious", "Lunarite Ore": "Precious", "Leystone Ore": "Precious",
    "Stardust Ore": "Mystic", "Aurorite Ore": "Mystic", "Empyrium Ore": "Mystic"
}

NAME_CASE_MAP = {k.lower(): k for k in list(ITEMS_DB.keys()) + list(BARS_DB.keys()) + list(ORES_DB.keys())}

# Helper om getallen te formatteren (k / M / B)
def format_num(val, compact=False):
    if not compact or not isinstance(val, (int, float)):
        return str(val) if isinstance(val, (int, float)) else val
    if val >= 1_000_000_000:
        res = f"{val / 1_000_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{res.replace('.', ',')}B"
    elif val >= 1_000_000:
        res = f"{val / 1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{res.replace('.', ',')}M"
    elif val >= 1_000:
        res = f"{val / 1_000:.1f}".rstrip('0').rstrip('.')
        return f"{res.replace('.', ',')}k"
    return str(val)

# Helper om handmatige tekstinvoer om te zetten naar getal
def parse_compact_input(val_str):
    if isinstance(val_str, (int, float)):
        return int(val_str)
    
    val_str = str(val_str).strip().lower().replace(' ', '')
    if not val_str:
        return 0
    
    multiplier = 1
    if val_str.endswith('b'):
        multiplier = 1_000_000_000
        val_str = val_str[:-1]
    elif val_str.endswith('m'):
        multiplier = 1_000_000
        val_str = val_str[:-1]
    elif val_str.endswith('k'):
        multiplier = 1_000
        val_str = val_str[:-1]
        
    val_str = val_str.replace(',', '.')
    try:
        return int(float(val_str) * multiplier)
    except ValueError:
        return 0

# ---------------------------------------------------------
# CALCULATION ENGINE (BRUTO EN NETTO HIËRARCHISCH)
# ---------------------------------------------------------
def parse_recipe(recipe_str):
    reqs = {}
    if not recipe_str:
        return reqs
    parts = recipe_str.split('+')
    for p in parts:
        p = p.strip()
        tokens = p.split('x ')
        if len(tokens) == 2:
            qty = int(tokens[0].replace(',', '').strip())
            name_raw = tokens[1].strip()
            name = NAME_CASE_MAP.get(name_raw.lower(), name_raw)
            reqs[name] = qty
    return reqs

def calculate_requirements(target_name, quantity, inventory):
    gross_items = {}
    gross_bars = {}
    gross_ores = {}

    # 1. PURE BRUTO BEREKENING (Van 0 af aan)
    def resolve_item_gross(name, qty):
        gross_items[name] = gross_items.get(name, 0) + qty
        recipe_str = ITEMS_DB.get(name, "")
        reqs = parse_recipe(recipe_str)
        for req_name, req_qty in reqs.items():
            tot_qty = req_qty * qty
            if req_name in ITEMS_DB:
                resolve_item_gross(req_name, tot_qty)
            elif req_name in BARS_DB:
                resolve_bar_gross(req_name, tot_qty)
            else:
                gross_ores[req_name] = gross_ores.get(req_name, 0) + tot_qty

    def resolve_bar_gross(name, qty):
        gross_bars[name] = gross_bars.get(name, 0) + qty
        recipe_str = BARS_DB.get(name, "")
        reqs = parse_recipe(recipe_str)
        for req_name, req_qty in reqs.items():
            tot_qty = req_qty * qty
            if req_name in BARS_DB:
                resolve_bar_gross(req_name, tot_qty)
            else:
                gross_ores[req_name] = gross_ores.get(req_name, 0) + tot_qty

    # 2. NETTO BEREKENING (Top-Down rekening houdend met tussentijdse voorraad)
    net_items = {}
    net_bars = {}
    net_ores = {}

    def resolve_item_net(name, qty_needed):
        in_stock = inventory.get(name, 0)
        actual_to_craft = max(0, qty_needed - in_stock)
        net_items[name] = net_items.get(name, 0) + qty_needed
        
        if actual_to_craft > 0:
            recipe_str = ITEMS_DB.get(name, "")
            reqs = parse_recipe(recipe_str)
            for req_name, req_qty in reqs.items():
                tot_qty = req_qty * actual_to_craft
                if req_name in ITEMS_DB:
                    resolve_item_net(req_name, tot_qty)
                elif req_name in BARS_DB:
                    resolve_bar_net(req_name, tot_qty)
                else:
                    net_ores[req_name] = net_ores.get(req_name, 0) + tot_qty

    def resolve_bar_net(name, qty_needed):
        in_stock = inventory.get(name, 0)
        actual_to_smelt = max(0, qty_needed - in_stock)
        net_bars[name] = net_bars.get(name, 0) + qty_needed
        
        if actual_to_smelt > 0:
            recipe_str = BARS_DB.get(name, "")
            reqs = parse_recipe(recipe_str)
            for req_name, req_qty in reqs.items():
                tot_qty = req_qty * actual_to_smelt
                if req_name in BARS_DB:
                    resolve_bar_net(req_name, tot_qty)
                else:
                    net_ores[req_name] = net_ores.get(req_name, 0) + tot_qty

    if target_name in ITEMS_DB:
        resolve_item_gross(target_name, quantity)
        resolve_item_net(target_name, quantity)
    elif target_name in BARS_DB:
        resolve_bar_gross(target_name, quantity)
        if target_name in gross_bars:
            del gross_bars[target_name]
            
        resolve_bar_net(target_name, quantity)
        if target_name in net_bars:
            del net_bars[target_name]

    return gross_items, gross_bars, gross_ores, net_items, net_bars, net_ores

def sort_by_tier(data_dict, order_list):
    sorted_dict = {}
    for item in order_list:
        if item in data_dict:
            sorted_dict[item] = data_dict[item]
    for k, v in data_dict.items():
        if k not in sorted_dict:
            sorted_dict[k] = v
    return sorted_dict

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if "inventory" not in st.session_state:
    st.session_state.inventory = {}

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

# ---------------------------------------------------------
# USER INTERFACE / CONTROLS
# ---------------------------------------------------------
st.sidebar.header("🎒 Instellingen & Voorraad")

if st.sidebar.button("🗑️ Wis Volledige Voorraad", use_container_width=True):
    st.session_state.inventory = {}
    st.session_state.reset_counter += 1
    st.rerun()

compact_view = st.sidebar.toggle(
    "Compacte getallenweergave",
    value=False,
    help="Schakel in om bijvoorbeeld 10.000 als 10k, 1.000.000 als 1M en 1.000.000.000 als 1B weer te geven."
)

all_options = ["--- CRAFTING ITEMS ---"] + ITEMS_ORDER + ["--- BARS / STAVEN ---"] + BARS_ORDER

col_select, col_qty = st.columns([3, 1])

with col_select:
    selected_option = st.selectbox(
        "Selecteer het te maken Item of Bar:",
        options=all_options,
        index=3,  # Standaard 'Battle axe'
        key="selected_item_choice"
    )

with col_qty:
    item_quantity = st.number_input(
        "Aantal te craften:",
        min_value=1,
        value=1,
        step=1,
        key="selected_item_qty"
    )

if selected_option.startswith("---"):
    st.warning("Kies a.u.b. een geldig Item of Bar uit de lijst.")
    st.stop()

# Voer de dynamische top-down berekening uit!
g_items, g_bars, g_ores, n_items, n_bars, n_ores = calculate_requirements(
    selected_option, 
    item_quantity, 
    st.session_state.inventory
)

# Sorteer op Tier
g_items = sort_by_tier(g_items, ITEMS_ORDER)
g_bars = sort_by_tier(g_bars, BARS_ORDER)
g_ores = sort_by_tier(g_ores, ORES_ORDER)

st.markdown("---")
st.header(f"Berekening voor {item_quantity}x {selected_option}")
st.info("💡 **Tip:** Vul je voorraad in bij tussen-items of staven; de benodigde ertsen worden automatisch mee verlaagd!")

cnt = st.session_state.reset_counter

# ---------------------------------------------------------
# INTERACTIVE DATA EDITORS FOR RESULTS
# ---------------------------------------------------------

# 1. ERTSEN / ORES
with st.expander("⛏️ Totaal Ertsen (Ores)", expanded=True):
    ores_data = []
    for ore_name, gross_qty in g_ores.items():
        in_stock = st.session_state.inventory.get(ore_name, 0)
        net_from_recipes = n_ores.get(ore_name, 0)
        
        # Trek ook de eigen erts-voorraad af van wat nog vanuit de recepten overbleef
        net_to_mine = max(0, net_from_recipes - in_stock)
        rarity = ORES_DB.get(ore_name, "Onbekend")
        
        ores_data.append({
            "Ore Naam": ore_name,
            "Bruto Nodig": format_num(gross_qty, compact_view),
            "In Voorraad ✏️": format_num(in_stock, compact_view),
            "Netto Nog Mijnen": format_num(net_to_mine, compact_view),
            "Zeldzaamheid": rarity
        })
    
    if ores_data:
        ores_df = pd.DataFrame(ores_data)
        edited_ores = st.data_editor(
            ores_df,
            column_config={
                "Ore Naam": st.column_config.TextColumn(disabled=True),
                "Bruto Nodig": st.column_config.TextColumn(disabled=True),
                "In Voorraad ✏️": st.column_config.TextColumn(disabled=False),
                "Netto Nog Mijnen": st.column_config.TextColumn(disabled=True),
                "Zeldzaamheid": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_ores_{cnt}"
        )
        for _, row in edited_ores.iterrows():
            name = row["Ore Naam"]
            parsed_val = parse_compact_input(row["In Voorraad ✏️"])
            if st.session_state.inventory.get(name, 0) != parsed_val:
                st.session_state.inventory[name] = parsed_val
                st.rerun()
    else:
        st.info("Geen ertsen nodig voor deze selectie.")

# 2. STAVEN / BARS
with st.expander("🔥 Totaal Staven (Bars)", expanded=True):
    bars_data = []
    for bar_name, gross_qty in g_bars.items():
        in_stock = st.session_state.inventory.get(bar_name, 0)
        net_needed_base = n_bars.get(bar_name, 0)
        net_to_smelt = max(0, net_needed_base - in_stock)
        
        bars_data.append({
            "Bar Naam": bar_name,
            "Bruto Nodig": format_num(gross_qty, compact_view),
            "In Voorraad ✏️": format_num(in_stock, compact_view),
            "Netto Nog Smelten": format_num(net_to_smelt, compact_view)
        })
    
    if bars_data:
        bars_df = pd.DataFrame(bars_data)
        edited_bars = st.data_editor(
            bars_df,
            column_config={
                "Bar Naam": st.column_config.TextColumn(disabled=True),
                "Bruto Nodig": st.column_config.TextColumn(disabled=True),
                "In Voorraad ✏️": st.column_config.TextColumn(disabled=False),
                "Netto Nog Smelten": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_bars_{cnt}"
        )
        for _, row in edited_bars.iterrows():
            name = row["Bar Naam"]
            parsed_val = parse_compact_input(row["In Voorraad ✏️"])
            if st.session_state.inventory.get(name, 0) != parsed_val:
                st.session_state.inventory[name] = parsed_val
                st.rerun()
    else:
        st.info("Geen staven nodig voor deze selectie.")

# 3. TUSSEN-ITEMS / CRAFTING TREE
with st.expander("📦 Tussen-Items (Crafting Tree)", expanded=False):
    items_data = []
    for it_name, gross_qty in g_items.items():
        in_stock = st.session_state.inventory.get(it_name, 0)
        net_needed_base = n_items.get(it_name, 0)
        net_to_craft = max(0, net_needed_base - in_stock)
        
        items_data.append({
            "Item Naam": it_name,
            "Bruto Nodig": format_num(gross_qty, compact_view),
            "In Voorraad ✏️": format_num(in_stock, compact_view),
            "Netto Nog Craften": format_num(net_to_craft, compact_view)
        })
    
    if items_data:
        items_df = pd.DataFrame(items_data)
        edited_items = st.data_editor(
            items_df,
            column_config={
                "Item Naam": st.column_config.TextColumn(disabled=True),
                "Bruto Nodig": st.column_config.TextColumn(disabled=True),
                "In Voorraad ✏️": st.column_config.TextColumn(disabled=False),
                "Netto Nog Craften": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_items_{cnt}"
        )
        for _, row in edited_items.iterrows():
            name = row["Item Naam"]
            parsed_val = parse_compact_input(row["In Voorraad ✏️"])
            if st.session_state.inventory.get(name, 0) != parsed_val:
                st.session_state.inventory[name] = parsed_val
                st.rerun()
    else:
        st.info("Geen tussen-items nodig voor deze selectie.")

# ---------------------------------------------------------
# DATABASE VIEW
# ---------------------------------------------------------
with st.expander("🔍 Bekijk de volledige recepten-database (27 Items, 19 Bars, 18 Ores)"):
    tab1, tab2, tab3 = st.tabs(["Crafting Items", "Bars", "Ores"])
    
    with tab1:
        st.dataframe(pd.DataFrame(list(ITEMS_DB.items()), columns=["Item Naam", "Receptuur"]), use_container_width=True)
    with tab2:
        st.dataframe(pd.DataFrame(list(BARS_DB.items()), columns=["Bar Naam", "Receptuur"]), use_container_width=True)
    with tab3:
        st.dataframe(pd.DataFrame(list(ORES_DB.items()), columns=["Ore Naam", "Zeldzaamheid"]), use_container_width=True)