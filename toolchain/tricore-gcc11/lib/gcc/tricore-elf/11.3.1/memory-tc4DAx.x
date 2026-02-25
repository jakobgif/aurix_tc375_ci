/*
 * memory.x -- The default memory description
 *
 * Copyright (C) 2009-2014 HighTec EDV-Systeme GmbH.
 *
 */
/*
    E_._._.: eXternal memory
    I_._._.: Internal memory
    P_._._.: PCP memory

    ._C_._.: Code
    ._D_._.: Data

    ._._R_.: RAM
    ._._F_.: Flash

    ._._._B: Base address
    ._._._S: Size
*/
/* Values taken from TC4 iLLDs */
__USTACK_SIZE = 2K;
__ISTACK_SIZE = 1k;
__HEAP_MIN = 4K;
__CSA_SIZE = 8K;
__TRICORE_DERIVATE_MEMORY_MAP__ = 0x4D00;
/* the external RAM description */
__EXT_CODE_RAM_BEGIN = 0;
__EXT_CODE_RAM_SIZE = 0 ;
__EXT_DATA_RAM_BEGIN = 0;
__EXT_DATA_RAM_SIZE = 0;
__RAM_END = __EXT_DATA_RAM_BEGIN + __EXT_DATA_RAM_SIZE;
/* internal FLASH description */
__INT_CODE_FLASH_BEGIN = 0x80000000;
__INT_CODE_FLASH_SIZE = 4M;
__INT_CODE_FLASH_BANK1_BEGIN = 0x80400000;
__INT_CODE_FLASH_BANK1_SIZE = 4M;
__INT_CODE_FLASH_BANK2_BEGIN = 0x80800000;
__INT_CODE_FLASH_BANK2_SIZE = 2M;
__INT_CODE_FLASH_BANK3_BEGIN = 0x80A00000;
__INT_CODE_FLASH_BANK3_SIZE = 4M;
__INT_CODE_FLASH_BANK4_BEGIN = 0x80E00000;
__INT_CODE_FLASH_BANK4_SIZE = 4M;
__INT_CODE_FLASH_BANK5_BEGIN = 0x81200000;
__INT_CODE_FLASH_BANK5_SIZE = 2M;
__INT_DATA_FLASH_BEGIN = 0xAE000000;
__INT_DATA_FLASH_SIZE = 1M;
/* the internal ram description */
__INT_CODE_RAM_BEGIN = 0xC0000000;
__INT_CODE_RAM_SIZE = 64K;
__INT_DATA_RAM_BEGIN = 0xD0000000;
__INT_DATA_RAM_SIZE = 240K;
/* the pcp memory description */
__PCP_CODE_RAM_BEGIN = 0;
__PCP_CODE_RAM_SIZE = 0;
__PCP_DATA_RAM_BEGIN = 0;
__PCP_DATA_RAM_SIZE = 0;
MEMORY
{
  PMU_PFLASH0 (rx!p): org = 0x80000000, len = 4M
  PMU_PFLASH1 (rx!p): org = 0x80400000, len = 4M
  PMU_PFLASH2 (rx!p): org = 0x80800000, len = 2M
  PMU_PFLASH3 (rx!p): org = 0x80A00000, len = 4M
  PMU_PFLASH4 (rx!p): org = 0x80E00000, len = 4M
  PMU_PFLASH5 (rx!p): org = 0x81200000, len = 2M
  PMU_DFLASH0 (w!xp): org = 0xAE000000, len = 1M
  PMI_SPRAM (rx!p): org = 0xC0000000, len = 64K
  DMI_LDRAM (w!xp): org = 0xD0000000, len = 240K
  PCP_PRAM (wp!x): org = 0, len = 0
  PCP_CMEM (rpx): org = 0, len = 0
}
REGION_ALIAS("DATA_MEM", DMI_LDRAM)
REGION_ALIAS("CODE_MEM", PMU_PFLASH0)
REGION_ALIAS("SDATA_MEM", DMI_LDRAM)
REGION_ALIAS("BSS_MEM", DMI_LDRAM)
REGION_ALIAS("ZDATA_MEM", DMI_LDRAM)
REGION_ALIAS("CSA_MEM", DMI_LDRAM)
REGION_ALIAS("PCP_CODE", PCP_CMEM)
REGION_ALIAS("PCP_DATA", PCP_PRAM)
/* the symbol __TRICORE_DERIVATE_NAME__ will be defined in the crt0.S and is
 * tested here to confirm that this memory map and the startup file will
 * fit together
*/
_. = ASSERT ((__TRICORE_DERIVATE_MEMORY_MAP__ == __TRICORE_DERIVATE_NAME__), "Using wrong Memory Map. This Map is for TC4Dxx");
INSERT BEFORE .startup
