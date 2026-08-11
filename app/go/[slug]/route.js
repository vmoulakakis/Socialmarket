import { NextResponse } from 'next/server';

const LINKS = {
  "01-timberland-scar-ridge-waterproof-p": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Ftb0a22w2433%3Fvariant%3D57472037552511%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "02-sebago-askook-lug-suede-waxed-l781": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Fsebago-andrika-papoutsia-dermatina-istioploika-askook-lug-suede-waxed-l781289w-906r-kafe%3Fvariant%3D58059898290559%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "03-la-martina-sneakers-3lfm261010-1a0": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Fla-martina-sneakers-3lfm261010-1a012%3Fvariant%3D57628691956095%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "04-fred-perry-caban-jacket-j8535-102": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F55283%3Fvariant%3D57466828128639%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "05-fred-perry-hooded-insulated-jacket": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Fj8553-184%3Fvariant%3D57472027591039%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "06-pepe-jeans-joey-pm4027178-999": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Fpm4027178-999%3Fvariant%3D57471814664575%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "07-the-bostonians-3wl00112-b795br": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F3wl00112-b795br%3Fvariant%3D57472065438079%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "08-fred-perry-insulated-jacket-j4564": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F46264-1-2-2%3Fvariant%3D57466605175167%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "09-salvatore-ferragamo-sf830s-001-48m": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fsalvatore-ferragamo-sf830s-001-48mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D2752",
  "10-monte-napoleone-251-71-6500-7046-4": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F251-71-6500-7046-4%3Fvariant%3D57467568324991%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "11-la-martina-polo-mcp321pk001-09999": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Fmcp321pk001-09999%3Fvariant%3D57472251429247%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "12-vittorio-100-25-azzuro-fanco": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Fvittorio-100-25-azzuro-fanco%3Fvariant%3D57471784943999%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "13-vittorio-100-25-roma-light-blue": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F100-25-roma-light-blue%3Fvariant%3D57471391072639%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "14-columbia-bugaboo-iii-fleece-jacket": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F2096904-258%3Fvariant%3D57471672582527%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "15-timberland-water-resistant-bomber": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F49491-1-3-1%3Fvariant%3D57465163350399%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "16-sportmax-sm0021-01a-55mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fsportmax-sm0021-01a-55mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D5715",
  "17-sportmax-sm0026-01a-57mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fsportmax-sm0026-01a-57mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D5721",
  "18-columbia-tunnel-fallstm-ii-interch": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2F51626-1%3Fvariant%3D57466584138111%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "19-marc-by-marc-jacobs-mmj-409-s-6wo": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fmarc-by-marc-jacobs-mmj-409-s-6w0-56mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D1675",
  "20-marc-jacobs-marc-733-s-szjha-52mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fmarc-jacobs-marc-733-s-szjha-52mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D12314",
  "21-marc-jacobs-mj-1013-s-8079o-56mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fmarc-jacobs-mj-1013-s-8079o-56mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D1651",
  "22-police-spl836-300l-57mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fpolice-spl836-300l-57mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D9567",
  "23-marc-jacobs-mj-1061-s-7c59o-59mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fmarc-jacobs-mj-1061-s-7c59o-59mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D7005",
  "24-sportmax-sm0011-01b-58mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fsportmax-sm0011-01b-58mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D5733",
  "25-timberland-hudson-road-mid-lace-gt": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Ftb0a6a8nw07%3Fvariant%3D57471561171327%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog",
  "26-chloe-ce114st-810-58mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fchloe-ce114st-810-58mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D5252",
  "27-marc-by-marc-jacobs-mmj-630-avq-54": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fmarc-by-marc-jacobs-mmj-630-avq-54mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D1728",
  "28-marc-jacobs-marc-738-s-79dt4-61mm": "https://go.linkwi.se/z/13703-0/CD104/?lnkurl=https%3A%2F%2Famorvisual.gr%2Fproduct%2Fmarc-jacobs-marc-738-s-79dt4-61mm%2F%3Futm_source%3DSkroutz%26utm_campaign%3Dskroutz%26utm_medium%3Dcpc%26utm_term%3D12321",
  "29-gucci-gucci-1835s-006-5218-1835s": "https://go.linkwi.se/z/12261-0/CD104/?lnkurl=https%3A%2F%2Fwww.markakis.gr%3A443%2Fel%2F%CE%93%CE%A5%CE%91%CE%9B%CE%99%CE%91%2520%CE%97%CE%9B%CE%99%CE%9F%CE%A5%2520GUCCI%25201835S%2520006%25205218-277638",
  "30-lacoste-sneakers-elite-active-sma0": "https://go.linkwi.se/z/13700-0/CD104/?lnkurl=https%3A%2F%2Ftobros.gr%2Fproducts%2Flacoste-sneakers-elite-active-sma004121g%3Fvariant%3D57628675080575%26utm_source%3Dlinkwise%26utm_medium%3Daffiliate%26utm_campaign%3Dcatalog"
};

export async function GET(_request, { params }) {
  const { slug } = await params;
  const target = LINKS[slug];

  if (!target) {
    return NextResponse.json({ error: 'Unknown campaign link' }, { status: 404 });
  }

  return NextResponse.redirect(target, 302);
}
