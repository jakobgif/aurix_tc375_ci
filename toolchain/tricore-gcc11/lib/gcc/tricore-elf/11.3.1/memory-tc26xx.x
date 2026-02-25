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
__USTACK_SIZE = 4K;
__ISTACK_SIZE = 256;
__HEAP_MIN = 8K;
__CSA_SIZE = 16K;
__TRICORE_DERIVATE_MEMORY_MAP__ = 0x2600;
/* the external RAM description */
__EXT_CODE_RAM_BEGIN = 0;
__EXT_CODE_RAM_SIZE = 0 ;
__EXT_DATA_RAM_BEGIN = 0;
__EXT_DATA_RAM_SIZE = 0;
__RAM_END = __EXT_DATA_RAM_BEGIN + __EXT_DATA_RAM_SIZE;
/* internal FLASH description */
__INT_CODE_FLASH_BEGIN = 0x80000000;
__INT_CODE_FLASH_SIZE = 0x100000;
__INT_CODE_FLASH_BANK1_BEGIN = 0x80100000;
__INT_CODE_FLASH_BANK1_SIZE = 0x180000;
__INT_DATA_FLASH_BEGIN = 0xaf000000;
__INT_DATA_FLASH_SIZE = 96K;
/* the internal ram description */
__INT_CODE_RAM_BEGIN = 0xc0000000;
__INT_CODE_RAM_SIZE = 16K;
__INT_DATA_RAM_BEGIN = 0xd0000000;
__INT_DATA_RAM_SIZE = 72K;
/* the pcp memory description */
__PCP_CODE_RAM_BEGIN = 0;
__PCP_CODE_RAM_SIZE = 0;
__PCP_DATA_RAM_BEGIN = 0;
__PCP_DATA_RAM_SIZE = 0;
MEMORY
{
  PMU_PFLASH0 (rx!p): org = 0x80000000, len = 0x100000
  PMU_PFLASH1 (rx!p): org = 0x80100000, len = 0x180000
  PMU_DFLASH0 (w!xp): org = 0xaf000000, len = 96K
  PMI_SPRAM (rx!p): org = 0xc0000000, len = 16K
  DMI_LDRAM (w!xp): org = 0xd0000000, len = 72K
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
_. = ASSERT ((__TRICORE_DERIVATE_MEMORY_MAP__ == __TRICORE_DERIVATE_NAME__), "Using wrong Memory Map. This Map is for TC26XX");
INSERT BEFORE .startup
