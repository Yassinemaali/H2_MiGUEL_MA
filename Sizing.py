import pandas as pd
import plotly as plot


class Sizing:
    def __init__(self, df):
        """
        df: Pandas DataFrame mit Zeitindex, Spalten 'P [W]', 'PV [W]'
        """
        self.df = df.copy()
        self._prepare_data()
        self.result = {}

    def _prepare_data(self, winter_months=[9,10,11,12]):
        def is_winter(ts):
            return ts.month in winter_months

        self.df['Season'] = self.df.index.map(lambda ts: 'Winter' if is_winter(ts) else 'Sommer')

    def summary(self):
        res = {
            "Gesamter Zeitraum": f"{self.df.index.min()} - {self.df.index.max()}",
            "Anzahl Datenpunkte": len(self.df),
            "Peak-Last [W]": self.df['P [W]'].max(),
            "Peak-PV [W]": self.df['PV [W]'].max(),
            "Durchschnittliche Tageslast [kWh]": round(self.df['P [W]'].resample('D').sum().mean() / 1000, 2)
        }
        print("\n".join([f"{k}: {v}" for k, v in res.items()]))
        print("---")
        return res

    def season_energy(self, season='Sommer'):
        mask = self.df['Season'] == season
        load_kwh = self.df.loc[mask, 'P [W]'].sum() / 1000
        pv_kwh = self.df.loc[mask, 'PV [W]'].sum() / 1000
        print(f"\n--- {season} ---")
        print("Anzahl Stunden:", mask.sum())
        print("Gesamtlast [kWh]:", round(load_kwh, 2))
        print("PV-Gesamt [kWh]:", round(pv_kwh, 2))
        return {'load_kwh': load_kwh, 'pv_kwh': pv_kwh}

    def run(self):
        # Führe alle Kernanalysen aus
        print("===== Gesamtauswertung =====")
        self.result['summary'] = self.summary()
        self.result['sommer'] = self.season_energy('Sommer')
        self.result['winter'] = self.season_energy('Winter')

        print("===== Fertig =====")
        return self.result

    def pv_dimensionierung(self, sfl=0.7, sfpv=1.1, eta_el=0.7, eta_fc=0.6):
        # 1. Gesamtlast Sommer & Winter berechnen (nach Season-Logik im df)
        df=self.df
        sommer_kwh = df[df['Season'] == 'Sommer']['P [W]'].sum() / 1000
        winter_kwh = df[df['Season'] == 'Winter']['P [W]'].sum() / 1000

        # 2. Jährlicher PV-spezifischer Ertrag aus deinen Daten (PV [W] pro Jahr / 1000 / installierte kW)
        # Angenommen, df['PV [W]'] ist für 100 kWp-Modul, also 100 kW!
        pv_kwh_year = df['PV [W]'].sum() / 1000 / 100  # Ertrag pro 1 kW [kWh/Jahr]

        # 3. Formeln nach Paper
        E_pv_sommer = sfpv * sommer_kwh
        E_pv_ele_winter = sfpv * (1 - sfl) * winter_kwh
        E_pv_H2_winter = sfpv * sfl * winter_kwh / (eta_el * eta_fc)
        E_pv_total = E_pv_sommer + E_pv_ele_winter + E_pv_H2_winter

        Cap_PV = E_pv_total / pv_kwh_year

        # Ausgabe
        print(f"Sommerlast [kWh]: {sommer_kwh:.0f}")
        print(f"Winterlast [kWh]: {winter_kwh:.0f}")
        print(f"PV-spezifischer Jahresertrag [kWh/kW]: {pv_kwh_year:.0f}")
        print(f"Erforderliche jährliche PV-Erzeugung [kWh]: {E_pv_total:.0f}")
        print(f"Empfohlene PV-Kapazität: {Cap_PV:.1f} kWp")
        return Cap_PV, {
        "E_pv_total": E_pv_total,
        "pv_kwh_year": pv_kwh_year,
        "E_pv_sommer": E_pv_sommer,
        "E_pv_ele_winter": E_pv_ele_winter,
        "E_pv_H2_winter": E_pv_H2_winter,
        "sommer_kwh": sommer_kwh,
        "winter_kwh": winter_kwh
    }
    def batterie_dimensionierung(self, sf_bat=1.1, dod_max=0.9):
        """
        Berechnet die benötigte Batteriegröße [kWh] für das System.
        sf_bat: Sizing-Faktor (Anzahl Autarkietage, Standard = 2)
        dod_max: maximal erlaubte Entladetiefe (z.B. 0.8)
        """
        # Mittelwert Tagesverbrauch im Jahr
        self.df['Load_kWh'] = self.df['P [W]'] / 1000
        mean_daily = self.df['Load_kWh'].resample('D').sum().mean()
        cap_bat = sf_bat * mean_daily / dod_max
        print(f"Durchschnittlicher Tagesverbrauch [kWh]: {mean_daily:.2f}")
        print(f"Batteriegröße: {cap_bat:.2f} kWh (für {sf_bat} Autarkietage, DOD={dod_max})")
        return cap_bat

    def fuelcell_dimensionierung(self):
        """
        Berechnet die benötigte Fuel-Cell-Leistung [kW] (Peaklast im Jahr).
        """
        peak_load = self.df['P [W]'].max() / 1000  # in kW
        print(f"Peak-Last im Jahr: {peak_load:.2f} kW")
        print(f"Empfohlene Brennstoffzellen-Leistung: {peak_load:.2f} kW")
        return peak_load

    def h2storage_dimensionierung(self, sfl=0.7, eta_fc=0.6):
        """
        Berechnet die benötigte Wasserstoffspeicher-Kapazität [kg].
        sfl: Load sizing factor (Anteil Winterlast über H2)
        eta_fc: Fuel-Cell-Wirkungsgrad [kWh/kg H2]
        """
        # Gesamtlast Winter (kWh)
        winter_kwh = self.df[self.df['Season'] == 'Winter']['P [W]'].sum() / 1000
        h2_needed = sfl * winter_kwh /(33.33*eta_fc)
        print(f"Winterlast [kWh]: {winter_kwh:.0f}")
        print(f"Empfohlene H2-Speichergröße: {h2_needed:.2f} kg (bei η_FC={eta_fc} kWh/kg, SFL={sfl})")
        return h2_needed

    def electrolyzer_dimensionierung(self, E_pv_H2_winter, eshd_ave=5, printout=True):
        """
        Berechnet die benötigte Elektrolyseur-Leistung [kW].
        E_pv_H2_winter: Energie für H2-Produktion im Winter (aus PV-Sizing) [kWh]
        eshd_ave: durchschnittliche Sonnenstunden pro Sommertag [h]
        """
        # Anzahl Sommertage (für Season='Sommer')
        days_sommer = self.df[self.df['Season'] == 'Sommer'].resample('D').sum().shape[0]
        cap_el = E_pv_H2_winter / (eshd_ave * days_sommer)
        if printout:
            print(f"Sommertage: {days_sommer}")
            print(f"Durchschnittliche Sonnenstunden/Tag: {eshd_ave}")
            print(f"Empfohlene Elektrolyseur-Leistung: {cap_el:.2f} kW")
        return cap_el

    def h2storage_dimensionierung_worstweek(self, eta_fc=0.6, sicherheitsfaktor=1.2):
        """
        Berechnet die benötigte H2-Speichergröße [kg] basierend auf der Woche mit dem schlechtesten PV/Load-Verhältnis.
        eta_fc: Wirkungsgrad der Brennstoffzelle (z.B. 0.6)
        sicherheitsfaktor: z.B. 1.2 (20% Reserve)
        """
        HHV = 33.33  # Heizwert Wasserstoff [kWh/kg]

        # Wöchentlich aufsummieren
        df = self.df.copy()
        df['Load_kWh'] = df['P [W]'] / 1000
        df['PV_kWh'] = df['PV [W]'] / 1000
        wochen = df.resample('W').sum()
        wochen['PV_Load_Ratio'] = wochen['PV_kWh'] / wochen['Load_kWh']

        # Schlechteste Woche finden
        min_ratio_week = wochen['PV_Load_Ratio'].idxmin()
        min_ratio = wochen.loc[min_ratio_week, 'PV_Load_Ratio']
        schlechteste_woche_defizit = wochen.loc[min_ratio_week, 'Load_kWh'] - wochen.loc[min_ratio_week, 'PV_kWh']

        # H2-Speicherbedarf
        h2_needed = max(0, schlechteste_woche_defizit * sicherheitsfaktor / (eta_fc * HHV))

        print(f"\nSchlechteste Woche (niedrigstes PV/Load-Verhältnis): {min_ratio_week.strftime('%d.%m.%Y')}")
        print(f"Verhältnis PV/Load: {min_ratio:.2%}")
        print(f"Defizit in dieser Woche: {schlechteste_woche_defizit:.0f} kWh")
        print(
            f"Empfohlene H2-Speichergröße [kg]: {h2_needed:.2f} (inkl. {int((sicherheitsfaktor - 1) * 100)}% Reserve)")

        return h2_needed





