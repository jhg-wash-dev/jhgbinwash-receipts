import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, date
import io
import random
import textwrap
import decimal

st.set_page_config(page_title="JHG Receipt Generator", page_icon="🧾", layout="centered")

# ---------- Helpers ----------
def money(x):
    try:
        return f"${decimal.Decimal(str(x)).quantize(decimal.Decimal('0.01'))}"
    except Exception:
        return "$0.00"

def wrap(draw, text, font, max_width):
    """Wrap text to fit max pixel width."""
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def load_font(size, bold=False):
    # Use common fonts available in most environments; fall back to default if missing.
    candidates = []
    if bold:
        candidates += ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    candidates += ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

def make_receipt_image(data):
    W = 900
    pad = 48
    bg = (255, 255, 255)
    ink = (25, 25, 25)
    sub = (90, 90, 90)
    line = (220, 220, 220)

    # dynamic height
    base_h = 1050
    rows = len(data["services"])
    H = base_h + max(0, rows - 3) * 58

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    f_title = load_font(40, bold=True)
    f_h = load_font(26, bold=True)
    f = load_font(22, bold=False)
    f_b = load_font(22, bold=True)
    f_small = load_font(18, bold=False)

    y = pad

    # Logo
    if data["logo_bytes"]:
        try:
            logo = Image.open(io.BytesIO(data["logo_bytes"])).convert("RGBA")
            max_logo_w, max_logo_h = 140, 140
            logo.thumbnail((max_logo_w, max_logo_h))
            img.paste(logo, (pad, y), logo)
            lx = pad + logo.size[0] + 18
        except Exception:
            lx = pad
    else:
        lx = pad

    # Header text
    draw.text((lx, y), data["business_name"], font=f_title, fill=ink)
    y += 52
    draw.text((lx, y), data["tagline"], font=f_small, fill=sub)
    y += 28

    contact_line = " • ".join([p for p in [data["phone"], data["email"], data["city_state"]] if p])
    if contact_line:
        draw.text((lx, y), contact_line, font=f_small, fill=sub)
    y += 34

    # Receipt meta box
    box_top = y + 10
    box_h = 118
    draw.rounded_rectangle([pad, box_top, W - pad, box_top + box_h], radius=18, outline=line, width=2, fill=(250,250,250))
    mx = pad + 18
    my = box_top + 16

    left_meta = [
        ("Receipt / Recibo", data["receipt_no"]),
        ("Date / Fecha", data["service_date"]),
        ("Customer / Cliente", data["customer"] or "—"),
    ]
    right_meta = [
        ("Type / Tipo", data["service_type"]),
        ("Paid via / Pagado por", data["paid_via"]),
        ("Notes / Notas", data["notes"] or "—"),
    ]

    # two columns
    col_w = (W - 2*pad - 36) // 2
    for i,(k,v) in enumerate(left_meta):
        draw.text((mx, my + i*32), f"{k}: ", font=f_small, fill=sub)
        draw.text((mx + 210, my + i*32), str(v), font=f_small, fill=ink)

    rx = mx + col_w + 18
    for i,(k,v) in enumerate(right_meta):
        draw.text((rx, my + i*32), f"{k}: ", font=f_small, fill=sub)
        draw.text((rx + 235, my + i*32), str(v), font=f_small, fill=ink)

    y = box_top + box_h + 28

    # Items header
    draw.text((pad, y), "Service Details / Detalles del Servicio", font=f_h, fill=ink)
    y += 18
    draw.line([pad, y+18, W-pad, y+18], fill=line, width=2)
    y += 36

    # Table columns
    x_desc = pad
    x_qty = W - pad - 240
    x_unit = W - pad - 160
    x_total = W - pad - 0

    draw.text((x_desc, y), "Description / Descripción", font=f_b, fill=sub)
    draw.text((x_qty, y), "Qty", font=f_b, fill=sub)
    draw.text((x_unit, y), "Unit", font=f_b, fill=sub)
    draw.text((x_total-90, y), "Total", font=f_b, fill=sub)
    y += 26
    draw.line([pad, y+10, W-pad, y+10], fill=line, width=2)
    y += 26

    # Items rows
    subtotal = decimal.Decimal("0.00")
    for it in data["services"]:
        desc = it["desc"]
        qty = decimal.Decimal(str(it["qty"]))
        unit = decimal.Decimal(str(it["unit"]))
        row_total = (qty * unit).quantize(decimal.Decimal("0.01"))
        subtotal += row_total

        # wrap description
        max_desc_w = x_qty - x_desc - 20
        lines = wrap(draw, desc, f, max_desc_w)
        draw.text((x_desc, y), lines[0], font=f, fill=ink)
        for j in range(1, len(lines)):
            draw.text((x_desc, y + j*24), lines[j], font=f, fill=ink)

        draw.text((x_qty, y), str(qty), font=f, fill=ink)
        draw.text((x_unit, y), money(unit), font=f, fill=ink)
        draw.text((x_total-90, y), money(row_total), font=f, fill=ink)

        y += max(48, 24*len(lines) + 12)
        draw.line([pad, y, W-pad, y], fill=(245,245,245), width=2)
        y += 14

    tax = decimal.Decimal(str(data["tax"])).quantize(decimal.Decimal("0.01"))
    total = (subtotal + tax).quantize(decimal.Decimal("0.01"))

    # Summary box
    y += 16
    sum_w = 340
    sx1 = W - pad - sum_w
    sx2 = W - pad
    draw.rounded_rectangle([sx1, y, sx2, y+180], radius=18, outline=line, width=2, fill=(250,250,250))
    yy = y + 18
    draw.text((sx1+18, yy), "Summary / Resumen", font=f_b, fill=ink); yy += 34
    draw.text((sx1+18, yy), "Subtotal:", font=f, fill=sub)
    draw.text((sx2-18-120, yy), money(subtotal), font=f, fill=ink); yy += 30
    draw.text((sx1+18, yy), "Tax / Impuesto:", font=f, fill=sub)
    draw.text((sx2-18-120, yy), money(tax), font=f, fill=ink); yy += 30
    draw.line([sx1+18, yy+6, sx2-18, yy+6], fill=line, width=2); yy += 18
    draw.text((sx1+18, yy), "Total:", font=f_b, fill=ink)
    draw.text((sx2-18-120, yy), money(total), font=f_b, fill=ink)

    # Footer
    fy = H - 120
    draw.line([pad, fy, W-pad, fy], fill=line, width=2)
    fy += 18
    footer = data["footer"]
    footer_lines = wrap(draw, footer, f_small, W - 2*pad)
    for i,ln in enumerate(footer_lines[:3]):
        draw.text((pad, fy + i*22), ln, font=f_small, fill=sub)

    return img, total

# ---------- UI ----------
st.title("🧾 Receipt Generator (Private) / Generador de Recibos (Privado)")

with st.expander("Business settings / Configuración del negocio", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business name / Nombre del negocio", value="JHG Bin Wash")
        phone = st.text_input("Phone / Teléfono", value="")
        email = st.text_input("Email / Correo", value="contact@jhgbinwash.com")
    with col2:
        city_state = st.text_input("City, State / Ciudad, Estado", value="Utah")
        tagline = st.text_input("Tagline / Frase corta", value="Tips rápidos y servicio profesional • Fast tips & professional service")
        logo_file = st.file_uploader("Logo (PNG/JPG) / Logo (PNG/JPG)", type=["png","jpg","jpeg"])

st.subheader("Receipt details / Detalles del recibo")
c1, c2 = st.columns(2)
with c1:
    customer = st.text_input("Customer name (optional) / Cliente (opcional)", value="")
    service_date = st.date_input("Service date / Fecha del servicio", value=date.today())
with c2:
    service_type = st.selectbox("Type / Tipo", ["One-time service / Servicio único", "Membership / Membresía"])
    paid_via = st.selectbox("Paid via / Pagado por", ["Cash / Efectivo", "Venmo", "Zelle", "Card / Tarjeta", "Other / Otro"])

notes = st.text_input("Notes (optional) / Notas (opcional)", value="")

st.markdown("### Items / Servicios")
if "services" not in st.session_state:
    st.session_state.services = [{"desc":"Bin cleaning / Lavado de bote", "qty":1, "unit":17.00}]

# Simple item editor
for idx, it in enumerate(st.session_state.services):
    cols = st.columns([6, 1.3, 1.7, 1])
    st.session_state.services[idx]["desc"] = cols[0].text_input(f"Description {idx+1}", value=it["desc"], key=f"desc_{idx}")
    st.session_state.services[idx]["qty"] = cols[1].number_input(f"Qty {idx+1}", min_value=1, value=int(it["qty"]), step=1, key=f"qty_{idx}")
    st.session_state.services[idx]["unit"] = cols[2].number_input(f"Unit ${idx+1}", min_value=0.0, value=float(it["unit"]), step=1.0, key=f"unit_{idx}")
    if cols[3].button("🗑️", key=f"del_{idx}"):
        st.session_state.services.pop(idx)
        st.rerun()

colA, colB = st.columns([1,1])
if colA.button("➕ Add service / Agregar servicio"):
    st.session_state.services.append({"desc":"", "qty":1, "unit":0.0})
    st.rerun()

tax = st.number_input("Tax (optional) / Impuesto (opcional)", min_value=0.0, value=0.0, step=0.5)

footer = st.text_input(
    "Footer (optional) / Pie de página (opcional)",
    value="Thank you for supporting a local business. • Gracias por apoyar un negocio local."
)

# Receipt number
default_no = f"JHG-{datetime.now().strftime('%y%m%d')}-{random.randint(1000,9999)}"
receipt_no = st.text_input("Receipt number / Número de recibo", value=default_no)

# Generate
logo_bytes = None
if logo_file is not None:
    logo_bytes = logo_file.read()

if st.button("✅ Generate receipt image / Generar recibo (imagen)"):
    # validate
    clean_items = []
    for it in st.session_state.services:
        if str(it["desc"]).strip() == "":
            continue
        clean_items.append({
            "desc": str(it["desc"]).strip(),
            "qty": int(it["qty"]),
            "unit": float(it["unit"]),
        })
    if not clean_items:
        st.error("Add at least one service / Agrega al menos un servicio.")
        st.stop()

    data = {
        "business_name": business_name.strip(),
        "tagline": tagline.strip(),
        "phone": phone.strip(),
        "email": email.strip(),
        "city_state": city_state.strip(),
        "receipt_no": receipt_no.strip(),
        "service_date": service_date.strftime("%Y-%m-%d"),
        "customer": customer.strip(),
        "service_type": service_type,
        "paid_via": paid_via,
        "notes": notes.strip(),
        "services": clean_items,
        "tax": float(tax),
        "footer": footer.strip(),
        "logo_bytes": logo_bytes,
    }

    img, total = make_receipt_image(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    st.success(f"Ready! Total: {money(total)} / Listo! Total: {money(total)}")
    st.image(png_bytes, caption="Receipt preview / Vista previa del recibo", use_container_width=True)

    st.download_button(
        "⬇️ Download PNG / Descargar PNG",
        data=png_bytes,
        file_name=f"{receipt_no.strip() or 'receipt'}.png",
        mime="image/png",
    )

    # Suggested message
    msg = f"""Hello! Here is your receipt from {business_name}.\nTotal: {money(total)}\nThank you!\n\nHola! Aquí está tu recibo de {business_name}.\nTotal: {money(total)}\n¡Gracias!"""
    st.text_area("Copy/paste message / Mensaje para copiar", value=msg, height=140)
