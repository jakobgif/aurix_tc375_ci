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
/* __TC13__ like __TC1920__ with Core TC1.3 */
__USTACK_SIZE = 1K;
__ISTACK_SIZE = 1K;
__HEAP_MIN = 4K;
__TRICORE_DERIVATE_MEMORY_MAP__ = 0x1920;
/* the external RAM description */
__EXT_CODE_RAM_BEGIN = 0xa0000000;
__EXT_CODE_RAM_SIZE = 512K ;
__EXT_DATA_RAM_BEGIN = 0xa0080000;
__EXT_DATA_RAM_SIZE = 512K;
__RAM_END = __EXT_DATA_RAM_BEGIN + __EXT_DATA_RAM_SIZE;
/* internal FLASH description */
__INT_CODE_FLASH_BEGIN = 0xa0000000;
__INT_CODE_FLASH_SIZE = 512K;
__INT_DATA_FLASH_BEGIN = 0xa0000000;
__INT_DATA_FLASH_SIZE = 512K;
/* the internal ram description */
__INT_CODE_RAM_BEGIN = 0xd4000000;
__INT_CODE_RAM_SIZE = 24K;
__INT_DATA_RAM_BEGIN = 0xd0000000;
__INT_DATA_RAM_SIZE = 24K;
/* the pcp memory description */
__PCP_CODE_RAM_BEGIN = 0xf0020000;
__PCP_CODE_RAM_SIZE = 16K;
__PCP_DATA_RAM_BEGIN = 0xf0010000;
__PCP_DATA_RAM_SIZE = 4K;
MEMORY
{
  PMU_PFLASH0 (rx!p): org = 0xa0000000, len = 512K
  PMU_DFLASH0 (w!xp): org = 0xa0000000, len = 512K
  PMI_SPRAM (rx!p): org = 0xd4000000, len = 24K
  DMI_LDRAM (w!xp): org = 0xd0000000, len = 24K
  PCP_PRAM (wp!x): org = 0xf0010000, len = 4K
  PCP_CMEM (rpx): org = 0xf0020000, len = 16K
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
_. = ASSERT ((__TRICORE_DERIVATE_MEMORY_MAP__ == __TRICORE_DERIVATE_NAME__), "Using wrong Memory Map. This Map is for TC13 like TC1920");
INSERT BEFORE .startup
