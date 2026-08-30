namespace JVLinkFetcher.Parsers;

// JV-Data 13. 競走馬マスタ (UM, 1609byte)
internal static class HorseCareerParser
{
    // 3代血統情報 (pos 205, 繰返14 × 46b)
    // [0]=父 [1]=母 [2]=父父 [3]=父母 [4]=母父 [5]=母母 [6-13]=3代
    private const int Pedigree_Start = 205;
    private const int Pedigree_Each  = 46;     // 繁殖登録番号(10) + 馬名(36)
    private const int Idx_Sire = 0, Idx_Dam = 1, Idx_BroodmareSire = 4;

    public static Dictionary<string, object?>? Parse(string rec)
    {
        if (rec.Length < 2 || rec[..2] != "UM") return null;
        try
        {
            var b = RecordParser.ToBytes(rec);
            if (b.Length < 50) return null;

            var horseCode    = RecordParser.F(b,  12, 10);
            var regDate      = RecordParser.F(b,  23,  8);
            var deregDate    = RecordParser.F(b,  31,  8);
            var birthDate    = RecordParser.F(b,  39,  8);
            var horseName    = RecordParser.F(b,  47, 36);
            var nameKana     = RecordParser.F(b,  83, 36);
            var nameEng      = RecordParser.F(b, 119, 60);
            var inJraFac     = RecordParser.F(b, 179,  1);
            var horseSym     = RecordParser.F(b, 199,  2);
            var sexCode      = RecordParser.F(b, 201,  1);
            var breedCode    = RecordParser.F(b, 202,  1);
            var colorCode    = RecordParser.F(b, 203,  2);

            var (sireCode, sireName) = ReadPedigree(b, Idx_Sire);
            var (damCode,  damName ) = ReadPedigree(b, Idx_Dam);
            var (bmsCode,  bmsName ) = ReadPedigree(b, Idx_BroodmareSire);

            var eastWest     = RecordParser.F(b, 849,  1);
            var trainerCode  = RecordParser.F(b, 850,  5);
            var trainerShort = RecordParser.F(b, 855,  8);
            var invitedArea  = RecordParser.F(b, 863, 20);
            var farmCode     = RecordParser.F(b, 883,  8);
            var farmName     = RecordParser.F(b, 891, 72);
            var farmArea     = RecordParser.F(b, 963, 20);
            var ownerCode    = RecordParser.F(b, 983,  6);
            var ownerName    = RecordParser.F(b, 989, 64);

            var flatPrize     = RecordParser.D(RecordParser.F(b, 1053, 9)) / 10.0;
            var obstaclePrize = RecordParser.D(RecordParser.F(b, 1062, 9)) / 10.0;

            var (totalRuns,   totalWins,   total2, total3) = Read6Counts(b, 1107);
            var (centralRuns, centralWins, _,      _     ) = Read6Counts(b, 1125);
            var (turfRunsA, turfWinsA, _, _) = Read6Counts(b, 1143);
            var (turfRunsB, turfWinsB, _, _) = Read6Counts(b, 1161);
            var (turfRunsC, turfWinsC, _, _) = Read6Counts(b, 1179);
            var (dirtRunsA, dirtWinsA, _, _) = Read6Counts(b, 1197);
            var (dirtRunsB, dirtWinsB, _, _) = Read6Counts(b, 1215);
            var (dirtRunsC, dirtWinsC, _, _) = Read6Counts(b, 1233);

            var regRaceCount = RecordParser.I(RecordParser.F(b, 1605, 3));

            if (string.IsNullOrEmpty(horseCode) || string.IsNullOrEmpty(horseName))
                return null;

            return new Dictionary<string, object?>
            {
                ["horse_code"]            = horseCode,
                ["horse_name"]            = horseName,
                ["horse_name_kana"]       = string.IsNullOrEmpty(nameKana) ? null : nameKana,
                ["horse_name_eng"]        = string.IsNullOrEmpty(nameEng)  ? null : nameEng,
                ["birth_year"]            = (object?)RecordParser.YearFromYMD(birthDate),
                ["birth_month"]           = (object?)RecordParser.MonthFromYMD(birthDate),
                ["birth_day"]             = (object?)(birthDate.Length >= 8 && int.TryParse(birthDate[6..8], out var d) ? d : null),
                ["sex_code"]              = string.IsNullOrEmpty(sexCode)   ? null : sexCode,
                ["breed_code"]            = string.IsNullOrEmpty(breedCode) ? null : breedCode,
                ["color_code"]            = string.IsNullOrEmpty(colorCode) ? null : colorCode,
                ["horse_symbol"]          = string.IsNullOrEmpty(horseSym)  ? null : horseSym,
                ["registered_date"]       = (object?)RecordParser.DateYMD(regDate),
                ["deregistered_date"]     = (object?)RecordParser.DateYMD(deregDate),
                ["in_jra_facility"]       = string.IsNullOrEmpty(inJraFac) ? null : inJraFac,
                ["sire_code"]             = string.IsNullOrEmpty(sireCode) ? null : sireCode,
                ["sire_name"]             = string.IsNullOrEmpty(sireName) ? null : sireName,
                ["dam_code"]              = string.IsNullOrEmpty(damCode)  ? null : damCode,
                ["dam_name"]              = string.IsNullOrEmpty(damName)  ? null : damName,
                ["broodmare_sire_code"]   = string.IsNullOrEmpty(bmsCode)  ? null : bmsCode,
                ["broodmare_sire_name"]   = string.IsNullOrEmpty(bmsName)  ? null : bmsName,
                ["east_west_code"]        = string.IsNullOrEmpty(eastWest)     ? null : eastWest,
                ["trainer_code"]          = string.IsNullOrEmpty(trainerCode)  ? null : trainerCode,
                ["trainer_name_short"]    = string.IsNullOrEmpty(trainerShort) ? null : trainerShort,
                ["invited_area"]          = string.IsNullOrEmpty(invitedArea)  ? null : invitedArea,
                ["farm_code"]             = string.IsNullOrEmpty(farmCode)  ? null : farmCode,
                ["farm_name"]             = string.IsNullOrEmpty(farmName)  ? null : farmName,
                ["farm_area"]             = string.IsNullOrEmpty(farmArea)  ? null : farmArea,
                ["owner_code"]            = string.IsNullOrEmpty(ownerCode) ? null : ownerCode,
                ["owner_name"]            = string.IsNullOrEmpty(ownerName) ? null : ownerName,
                ["flat_prize_total"]      = flatPrize,
                ["obstacle_prize_total"]  = obstaclePrize,
                ["total_runs"]            = totalRuns,
                ["total_wins"]            = totalWins,
                ["total_2nd"]             = total2,
                ["total_3rd"]             = total3,
                ["central_runs"]          = centralRuns,
                ["central_wins"]          = centralWins,
                ["turf_runs"]             = turfRunsA + turfRunsB + turfRunsC,
                ["turf_wins"]             = turfWinsA + turfWinsB + turfWinsC,
                ["dirt_runs"]             = dirtRunsA + dirtRunsB + dirtRunsC,
                ["dirt_wins"]             = dirtWinsA + dirtWinsB + dirtWinsC,
                ["registered_race_count"] = regRaceCount,
            };
        }
        catch { return null; }
    }

    private static (string code, string name) ReadPedigree(byte[] b, int index)
    {
        int pos = Pedigree_Start + index * Pedigree_Each;
        var code = RecordParser.F(b, pos,      10);
        var name = RecordParser.F(b, pos + 10, 36);
        return (code, name);
    }

    // 着回数 6個 (1着/2着/3着/4着/5着/着外) を読んで (runs, wins, 2着, 3着) を返す
    private static (int runs, int wins, int second, int third) Read6Counts(byte[] b, int pos)
    {
        int p1 = RecordParser.I(RecordParser.F(b, pos,      3));
        int p2 = RecordParser.I(RecordParser.F(b, pos +  3, 3));
        int p3 = RecordParser.I(RecordParser.F(b, pos +  6, 3));
        int p4 = RecordParser.I(RecordParser.F(b, pos +  9, 3));
        int p5 = RecordParser.I(RecordParser.F(b, pos + 12, 3));
        int po = RecordParser.I(RecordParser.F(b, pos + 15, 3));
        return (p1 + p2 + p3 + p4 + p5 + po, p1, p2, p3);
    }
}
