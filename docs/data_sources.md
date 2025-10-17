# Data Sources for TuExpertoFiscal NAIL

This document contains all the data sources that will be parsed and indexed into our knowledge base.

## 1. Spanish Tax Code (Налоговый кодекс Испании)

### Primary Laws

**Ley General Tributaria (LGT) - General Tax Law**
- **Law:** Ley 58/2003, de 17 de diciembre
- **Official Source:** BOE (Boletín Oficial del Estado)
- **URL:** https://www.boe.es/buscar/act.php?id=BOE-A-2003-23186
- **Format:** HTML/PDF
- **Update Frequency:** As amended (check quarterly)
- **Priority:** ⭐⭐⭐ CRITICAL

**IRPF - Personal Income Tax**
- **Law:** Ley 35/2006, de 28 de noviembre
- **URL:** https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764
- **Format:** HTML/PDF
- **Update Frequency:** Annual (each tax year)
- **Priority:** ⭐⭐⭐ CRITICAL

**IVA - Value Added Tax (VAT)**
- **Law:** Ley 37/1992, de 28 de diciembre
- **URL:** https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740
- **Format:** HTML/PDF
- **Update Frequency:** As amended
- **Priority:** ⭐⭐⭐ CRITICAL

**Impuesto sobre Sociedades - Corporate Tax**
- **Law:** Ley 27/2014, de 27 de noviembre
- **URL:** https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328
- **Format:** HTML/PDF
- **Update Frequency:** Annual
- **Priority:** ⭐⭐ HIGH

**Impuesto sobre Sucesiones y Donaciones - Inheritance & Gift Tax**
- **Law:** Ley 29/1987, de 18 de diciembre
- **URL:** https://www.boe.es/buscar/act.php?id=BOE-A-1987-28141
- **Format:** HTML/PDF
- **Priority:** ⭐⭐ HIGH

**Impuesto sobre el Patrimonio - Wealth Tax**
- **Law:** Ley 19/1991, de 6 de junio
- **URL:** https://www.boe.es/buscar/act.php?id=BOE-A-1991-13292
- **Format:** HTML/PDF
- **Priority:** ⭐ MEDIUM

## 2. Regional Tax Laws - Valencia (Comunidad Valenciana)

**Valencian Regional Tax Regulations**
- **Authority:** Generalitat Valenciana
- **URL:** https://www.gva.es/es/inicio/procedimientos?id_proc=290
- **DOGV (Official Gazette):** https://www.dogv.gva.es/
- **Key Topics:**
  - Regional income tax supplements
  - Inheritance tax rates (regional variations)
  - Property transfer tax (ITP)
  - Stamp duty (AJD)
- **Update Frequency:** Annual budget law + amendments
- **Priority:** ⭐⭐⭐ CRITICAL (for Valencia users)

**Specific Laws to Monitor:**
- Ley de Medidas Fiscales (annual budget law)
- Regional inheritance tax deductions
- First-time home buyer benefits

## 3. Spanish Tax Calendar (Calendario Fiscal)

**AEAT Official Tax Calendar**
- **Source:** Agencia Tributaria (Spanish Tax Agency)
- **URL:** https://sede.agenciatributaria.gob.es/Sede/ayuda/calendario-contribuyente.html
- **Format:** HTML/PDF/iCal
- **Content:**
  - Tax filing deadlines (IRPF, IVA, etc.)
  - Quarterly payment dates
  - Annual declaration periods
  - Important dates for autónomos
- **Update Frequency:** Annual (published in December for next year)
- **Priority:** ⭐⭐⭐ CRITICAL

## 4. Official AEAT Resources

**Agencia Tributaria Official Website**
- **URL:** https://sede.agenciatributaria.gob.es/
- **Sections to Parse:**
  - FAQs (Preguntas Frecuentes)
  - Tax forms and instructions (Modelos)
  - Calculators and tools
  - Guides for taxpayers
- **Update Frequency:** Ongoing
- **Priority:** ⭐⭐⭐ CRITICAL

## 5. Telegram Groups (Manual Export + Weekly Parser)

### Recommended Groups to Monitor
*(To be filled with specific group links)*

**Spanish Tax Discussion Groups:**
1. **IT Autonomos [Spain]**
   - **Link/ID:** https://t.me/it_autonomos_spain
   - **Topic:** IT Autónomos in Spain (self-employed in IT sector)
   - **Members:** ~4,281
   - **Activity Level:** 🔥 High
   - **Description:** Group for IT professionals working as autónomos in Spain. Discussions about taxes, reporting, dealing with AEAT, choosing tax rates.

2. **Чат Digital Nomad Spain 🇪🇸**
   - **Link/ID:** https://t.me/chatfornomads
   - **Topic:** Digital nomads in Spain, relocation, visas, taxation
   - **Members:** ~11,286
   - **Activity Level:** 🔥🔥 Very High
   - **Description:** Discussion of digital nomad visa, relocation, taxes for remote workers and freelancers. Very active community.

3. **Group Name:** [TO BE ADDED - if needed]
   - **Link/ID:** 
   - **Topic:** 
   - **Members:** 
   - **Activity Level:** 

**Implementation:**
- **Method:** Telethon/Pyrogram for automated parsing
- **Frequency:** Weekly (every Monday)
- **Filtering:** Remove spam, ads, off-topic messages
- **Extract:** Questions and high-quality answers
- **Priority:** ⭐⭐ HIGH

## 6. Tax News Sources (Daily Scraping)

**Spanish Financial/Tax News Sites:**

1. **Cinco Días (El País Economics)**
   - **URL:** https://cincodias.elpais.com/tag/impuestos/
   - **Topic:** Tax news and analysis
   - **RSS:** Available
   - **Priority:** ⭐⭐⭐ HIGH

2. **Expansión - Fiscalidad**
   - **URL:** https://www.expansion.com/economia/politica/fiscalidad.html
   - **Topic:** Tax policy and business taxes
   - **Priority:** ⭐⭐⭐ HIGH

3. **El Economista - Fiscal**
   - **URL:** https://www.eleconomista.es/economia/fiscal
   - **Topic:** Tax updates and expert opinions
   - **Priority:** ⭐⭐ MEDIUM

4. **Newtral - Fiscal**
   - **URL:** https://www.newtral.es/zona-verificacion/economia/
   - **Topic:** Fact-checking tax information
   - **Priority:** ⭐⭐ MEDIUM

## 7. Professional Tax Resources

**Tax Advisory Websites:**
- Garrigues (law firm): https://www.garrigues.com/es_ES/publicaciones?area=fiscalidad
- Cuatrecasas: Tax updates and insights
- REAF (Tax advisors association): https://www.reaf.es/

## 8. EU Tax Directives (for context)

**European Commission - Taxation**
- **URL:** https://taxation-customs.ec.europa.eu/
- **Relevant Directives:** VAT Directive, Anti-Tax Avoidance Directive
- **Priority:** ⭐ LOW (context only)

---

## Parsing Schedule

| Source Type | Frequency | Tool | Priority |
|-------------|-----------|------|----------|
| Tax Laws (BOE) | Quarterly | LangChain PDF/Web Loader | Critical |
| Valencia DOGV | Monthly | LangChain Web Loader | High |
| Tax Calendar | Annual | Manual + Parser | Critical |
| AEAT Website | Monthly | LangChain Web Loader | High |
| Telegram Groups | Weekly | Telethon/Pyrogram | High |
| News Sites | Daily | LangChain NewsURLLoader | Medium |

---

## Next Steps

1. ✅ Document created
2. [ ] User to add specific Telegram group links
3. [ ] Test parsing each source type
4. [ ] Create individual parser scripts for each category
5. [ ] Set up automated scheduling

---

*Developed by NAIL - Nahornyi AI Lab*
