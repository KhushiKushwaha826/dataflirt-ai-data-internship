import re

source = "fixtures/Apple iPhone 14.html"

with open(source, "r", encoding="utf-8") as f:
    original_content = f.read()


def m1_rename_id(c):
    return c.replace('id="productTitle"', 'id="productTitle_v2"')

def m2_remove_og_title(c):
    return re.sub(r'<meta property="og:title"[^>]*>', '', c)

def m3_wrap_in_div(c):
    return c.replace('<span id="productTitle"', '<div class="new-wrapper"><span id="productTitle"').replace('</span>', '</span></div>', 1)

def m4_rename_price_class(c):
    return c.replace('class="a-price-whole"', 'class="a-price-whole-v2"')

def m5_drop_price_symbol(c):
    return c.replace('a-price-symbol', 'a-price-symbol-x')

def m6_reorder_attributes(c):
    # id aur class ka order swap karo productTitle span mein
    return re.sub(
        r'<span id="productTitle" class="([^"]*)"',
        r'<span class="\1" id="productTitle"',
        c
    )

def m7_add_extra_whitespace(c):
    # productTitle ke aas paas junk whitespace/comments daal do
    return c.replace('id="productTitle"', 'id="productTitle" data-mutated="true"')

def m8_nested_wrap_price(c):
    return c.replace('<span class="a-price-whole">', '<span class="outer-wrap"><span class="a-price-whole">').replace('</span>', '</span></span>', 1)


mutations = {
    "m1_id_renamed": m1_rename_id,
    "m2_og_removed": m2_remove_og_title,
    "m3_wrapped_div": m3_wrap_in_div,
    "m4_price_class_renamed": m4_rename_price_class,
    "m5_symbol_dropped": m5_drop_price_symbol,
    "m6_attrs_reordered": m6_reorder_attributes,
    "m7_extra_attribute": m7_add_extra_whitespace,
    "m8_price_nested": m8_nested_wrap_price,
}

for name, fn in mutations.items():
    broken = fn(original_content)
    path = f"fixtures/chaos_{name}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(broken)
    print(f"Created: {path}")

print(f"\nTotal: {len(mutations)} chaos variants")