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

st.title("⚒️ Orecraft Miningtool ⚒️")

# ---------------------------------------------------------
# DATA LOADING FROM EXCEL (MATRIX STRUCTURE)
# ---------------------------------------------------------
@st.cache_data
def load_database_from_excel(file_path="orecraft_database.xlsx"):
    df = pd.read_excel(file_path)
    
    # Standardize column names
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # Identify meta columns and ingredient columns
    meta_cols = ["type", "naam", "zeldzaamheid"]
    ingredient_cols = [c for c in df.columns if c not in meta_cols]
    
    items_order = []
    items_db = {}
    
    bars_order = []
    bars_db = {}
    
    ores_order = []
    ores_db = {}

    types_map = {}
    
    for _, row in df.iterrows():
        row_type = str(row["type"]).strip().lower()
        item_name = str(row["naam"]).strip()
        types_map[item_name.lower()] = row_type
        
        # Build recipe dictionary from matrix columns (>0)
        recipe = {}
        for ing_col in ingredient_cols:
            val = row[ing_col]
            if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                recipe[ing_col] = int(val)
                
        if row_type == "item":
            items_order.append(item_name)
            items_db[item_name] = recipe
            
        elif row_type == "bar":
            bars_order.append(item_name)
            bars_db[item_name] = recipe
            
        elif row_type == "ore":
            ores_order.append(item_name)
            rarity = str(row["zeldzaamheid"]).strip() if pd.notna(row["zeldzaamheid"]) else "Onbekend"
            ores_db[item_name] = rarity

    # Mapping for case-insensitive lookup
    all_names = list(items_db.keys()) + list(bars_db.keys()) + list(ores_db.keys()) + [c.title() for c in ingredient_cols]
    name_case_map = {k.lower(): k for k in all_names}
    
    return items_order, items_db, bars_order, bars_db, ores_order, ores_db, name_case_map, types_map

# Load database
try:
    ITEMS_ORDER, ITEMS_DB, BARS_ORDER, BARS_DB, ORES_ORDER, ORES_DB, NAME_CASE_MAP, TYPES_MAP = load_database_from_excel()
except Exception as e:
    st.error(f"Fout bij het laden van het Excel-bestand 'orecraft_database.xlsx': {e}")
    st.stop()

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
# CALCULATION ENGINE (CASE-INSENSITIVE & RECURSIVE)
# ---------------------------------------------------------
def get_recipe_dict(name):
    name_lower = name.lower()
    for k, v in ITEMS_DB.items():
        if k.lower() == name_lower:
            return v
    for k, v in BARS_DB.items():
        if k.lower() == name_lower:
            return v
    return {}

def calculate_requirements(target_name, quantity, inventory):
    gross_items = {}
    gross_bars = {}
    gross_ores = {}

    # 1. BRUTO BEREKENING (Volledig recursief doorrekenen)
    def resolve_gross(name, qty):
        recipe = get_recipe_dict(name)
        for req_raw, req_qty in recipe.items():
            req_name = NAME_CASE_MAP.get(req_raw.lower(), req_raw)
            tot_qty = req_qty * qty
            req_type = TYPES_MAP.get(req_name.lower(), "unknown")

            if req_type == "item":
                gross_items[req_name] = gross_items.get(req_name, 0) + tot_qty
                resolve_gross(req_name, tot_qty)
            elif req_type == "bar":
                gross_bars[req_name] = gross_bars.get(req_name, 0) + tot_qty
                resolve_gross(req_name, tot_qty)
            else:
                gross_ores[req_name] = gross_ores.get(req_name, 0) + tot_qty

    # 2. NETTO BEREKENING (Top-Down rekening houdend met voorraad)
    net_items = {}
    net_bars = {}
    net_ores = {}

    def resolve_net(name, qty_needed):
        recipe = get_recipe_dict(name)
        for req_raw, req_qty in recipe.items():
            req_name = NAME_CASE_MAP.get(req_raw.lower(), req_raw)
            tot_qty = req_qty * qty_needed
            req_type = TYPES_MAP.get(req_name.lower(), "unknown")
            in_stock = inventory.get(req_name, 0)

            if req_type == "item":
                net_items[req_name] = net_items.get(req_name, 0) + tot_qty
                actual_to_craft = max(0, tot_qty - in_stock)
                if actual_to_craft > 0:
                    resolve_net(req_name, actual_to_craft)
            elif req_type == "bar":
                net_bars[req_name] = net_bars.get(req_name, 0) + tot_qty
                actual_to_smelt = max(0, tot_qty - in_stock)
                if actual_to_smelt > 0:
                    resolve_net(req_name, actual_to_smelt)
            else:
                net_ores[req_name] = net_ores.get(req_name, 0) + tot_qty

    resolve_gross(target_name, quantity)
    resolve_net(target_name, quantity)

    return gross_items, gross_bars, gross_ores, net_items, net_bars, net_ores

def sort_by_tier(data_dict, order_list):
    sorted_dict = {}
    for item in order_list:
        # Match case-insensitive
        matched_key = None
        for k in data_dict.keys():
            if k.lower() == item.lower():
                matched_key = k
                break
        if matched_key:
            sorted_dict[matched_key] = data_dict[matched_key]

    for k, v in data_dict.items():
        if k not in sorted_dict:
            sorted_dict[k] = v
    return sorted_dict

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
DEFAULT_PLACEHOLDER = " Selecteer een item of bar..."
HEADER_ITEMS = "📦 --- CRAFTING ITEMS ---"
HEADER_BARS = "🔥 --- BARS / STAVEN ---"

if "inventory" not in st.session_state:
    st.session_state.inventory = {}

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

if "selected_item_choice" not in st.session_state:
    st.session_state.selected_item_choice = DEFAULT_PLACEHOLDER

if "selected_item_qty" not in st.session_state:
    st.session_state.selected_item_qty = 1

# ---------------------------------------------------------
# USER INTERFACE / CONTROLS
# ---------------------------------------------------------
st.sidebar.header("🎒 Instellingen & Voorraad")

if st.sidebar.button("🗑️ Wis Volledige Voorraad", use_container_width=True):
    st.session_state.inventory = {}
    st.session_state.reset_counter += 1
    st.session_state.selected_item_choice = DEFAULT_PLACEHOLDER
    st.session_state.selected_item_qty = 1
    st.rerun()

compact_view = st.sidebar.toggle(
    "Compacte getallenweergave",
    value=False,
    help="Schakel in om bijvoorbeeld 10.000 als 10k, 1.000.000 als 1M en 1.000.000.000 als 1B weer te geven."
)

# Bouw ingesprongen lijst voor de dropdown met een duidelijke hiërarchie
options_map = {}
display_options = [DEFAULT_PLACEHOLDER, HEADER_ITEMS]

for item in ITEMS_ORDER:
    disp = f"   └─ {item}"
    display_options.append(disp)
    options_map[disp] = item

display_options.append(HEADER_BARS)
for bar in BARS_ORDER:
    disp = f"   └─ {bar}"
    display_options.append(disp)
    options_map[disp] = bar

col_select, col_qty = st.columns([3, 1])

with col_select:
    selected_disp = st.selectbox(
        "Selecteer het te maken Item of Bar:",
        options=display_options,
        key="selected_item_choice"
    )

with col_qty:
    item_quantity = st.number_input(
        "Aantal te craften:",
        min_value=1,
        step=1,
        key="selected_item_qty"
    )

if selected_disp == DEFAULT_PLACEHOLDER:
    st.info("👈 Selecteer bovenaan een item of bar om de ingrediënten te berekenen.")
    st.stop()

if selected_disp in [HEADER_ITEMS, HEADER_BARS]:
    st.warning("⚠️ Je hebt een categoriekop gekozen. Selecteer a.u.b. een specifiek item of bar eronder.")
    st.stop()

selected_option = options_map.get(selected_disp, selected_disp)

# Berekening uitvoeren
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
with st.expander("📦 Tussen-Items (Crafting Tree)", expanded=True):
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