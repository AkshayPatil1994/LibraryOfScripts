import numpy as np
import struct
from pathlib import Path
from tqdm import tqdm
#
# DEFINE uDALES WRITER CLASS
#
class uDALESRestartWriter:
    '''
        uDALES Restart Writer class with internal definitions
    '''
    
    def __init__(self, ib, ie, jb, je, kb, ke, ih=1, jh=1, kh=1, nprocx=1, nprocy=1):
        self.ib = ib
        self.ie = ie
        self.jb = jb
        self.je = je
        self.kb = kb
        self.ke = ke
        self.ih = ih
        self.jh = jh
        self.kh = kh
        self.nprocx = nprocx
        self.nprocy = nprocy
        
        self.nx = ie - ib + 1
        self.ny = je - jb + 1
        self.nz = ke - kb + 1
        
        self.nx_local = self.nx // nprocx
        self.ny_local = self.ny // nprocy
        
        if self.nx % nprocx != 0:
            raise ValueError(f"nx ({self.nx}) must be divisible by nprocx ({nprocx})")
        if self.ny % nprocy != 0:
            raise ValueError(f"ny ({self.ny}) must be divisible by nprocy ({nprocy})")
    
    def _write_fortran_record(self, f, data):
        '''
            Write one unformatted Fortran record with 4-byte record markers.
        '''
        if isinstance(data, np.ndarray):
            data_bytes = np.asfortranarray(data).tobytes(order='F')
        else:
            data_bytes = data
        nbytes = len(data_bytes)
        f.write(struct.pack('i', nbytes))
        f.write(data_bytes)
        f.write(struct.pack('i', nbytes))
    
    def write_restart_files(self, data_dict, output_dir='.', ntrun=0, cexpnr='001', nsv=0, 
                           auto_fill_zeros=False):
        '''
            Write all processor restart files.
        
        INPUT
            data_dict - [dict]: Dictionary with field data. If auto_fill_zeros=True, only 'timee' and 'dt' are required. Other fields will be initialized as zeros.
            output_dir - [str]: Output directory path
            ntrun - [int]: Run number
            cexpnr - [str]: Experiment number (3 characters)
            nsv - [int]: Number of scalar variables
            auto_fill_zeros - [bool]: If True, automatically create zero arrays for missing fields
        '''

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Check for required time fields
        if 'timee' not in data_dict or 'dt' not in data_dict:
            raise ValueError("Missing required fields: 'timee' and/or 'dt'")

        # Fill in missing fields with zeros if requested
        if auto_fill_zeros:
            data_dict = self._fill_missing_fields(data_dict)
        else:
            # Check all required fields are present
            required = ['mindist', 'wall', 'u0', 'v0', 'w0', 'pres0',
                       'thl0', 'e120', 'ekm', 'qt0', 'ql0', 'ql0h', 'timee', 'dt']
            for fkey in required:
                if fkey not in data_dict:
                    raise ValueError(f"Missing field: {fkey}. Set auto_fill_zeros=True to auto-generate.")

        for ipx in range(self.nprocx):
            for ipy in range(self.nprocy):
                self._write_processor_file(data_dict, ipx, ipy, output_path, ntrun, cexpnr, nsv)

        print(f"Successfully wrote {self.nprocx * self.nprocy} restart files to {output_dir}")

    def _fill_missing_fields(self, data_dict):
        '''
            Create zero arrays for any missing fields.
        '''
        nx_tot = self.nx + 2 * self.ih
        ny_tot = self.ny + 2 * self.jh
        nz_tot = self.nz + self.kh
        
        defaults = {
            'mindist': np.zeros((self.nx, self.ny, self.nz)),
            'wall': np.zeros((self.nx, self.ny, self.nz, 5)),
            'u0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'v0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'w0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'pres0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'thl0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'qt0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'ql0': np.zeros((nx_tot, ny_tot, nz_tot)),
            'ql0h': np.zeros((nx_tot, ny_tot, nz_tot)),
            'e120': np.zeros((nx_tot, ny_tot, nz_tot)),
            'ekm': np.zeros((nx_tot, ny_tot, nz_tot)),
        }
        
        # Update defaults with provided data
        result = defaults.copy()
        result.update(data_dict)
        return result

    def _write_processor_file(self, data, ipx, ipy, out_path, ntrun, cexpnr, nsv):
        '''
            Write one processor file matching Fortran record structure exactly.
        '''

        cmyidx = f"{ipx:03d}"
        cmyidy = f"{ipy:03d}"

        filename = f"initd{ntrun:08d}_{cmyidx}_{cmyidy}.{cexpnr}"
        filepath = out_path / filename

        i_off = ipx * self.nx_local
        j_off = ipy * self.ny_local

        i_start = i_off
        i_end = i_off + self.nx_local + 2 * self.ih
        j_start = j_off
        j_end = j_off + self.ny_local + 2 * self.jh

        with open(filepath, 'wb') as f:
            # 1. mindist (no ghost cells - ib:ie, jb:je, kb:ke)
            mindist = data['mindist'][
                i_off:i_off+self.nx_local,
                j_off:j_off+self.ny_local,
                :
            ]
            self._write_fortran_record(f, mindist)

            # 2. wall (5 components, no ghost cells) -> ONE record
            wall_block = data['wall'][
                i_off:i_off+self.nx_local,
                j_off:j_off+self.ny_local,
                :, :
            ]
            self._write_fortran_record(f, wall_block)

            # Fields with ghost cells
            for key in ['u0', 'v0', 'w0', 'pres0', 'thl0', 'e120', 'ekm', 'qt0', 'ql0', 'ql0h']:
                arr = data[key][i_start:i_end, j_start:j_end, :]
                self._write_fortran_record(f, arr)

            # 13. timee and dt
            self._write_fortran_record(f, np.array([data['timee'], data['dt']], dtype=np.float64))

        print(f"  Written: {filename}")

        # Scalar variables file (if any)
        if nsv > 0 and 'sv0' in data:
            filename_sv = f"inits{ntrun:08d}_{cmyidx}_{cmyidy}.{cexpnr}"
            filepath_sv = out_path / filename_sv
            with open(filepath_sv, 'wb') as f:
                sv_block = data['sv0'][i_start:i_end, j_start:j_end, :, :nsv]
                self._write_fortran_record(f, sv_block)
                self._write_fortran_record(f, np.array([data['timee']], dtype=np.float64))
            print(f"  Written: {filename_sv}")


def create_default_fields(nx, ny, nz, ih=1, jh=1, kh=1):
    '''
        Creates default fields based on input grid
    '''
    nx_tot, ny_tot, nz_tot = nx + 2*ih, ny + 2*jh, nz + kh
    return {
        'mindist': np.zeros((nx, ny, nz)),
        'wall': np.zeros((nx, ny, nz, 5)),
        'u0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'v0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'w0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'pres0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'thl0': np.ones((nx_tot, ny_tot, nz_tot)) * 288.0,
        'qt0': np.ones((nx_tot, ny_tot, nz_tot)) * 0.01,
        'ql0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'ql0h': np.zeros((nx_tot, ny_tot, nz_tot)),
        'e120': np.ones((nx_tot, ny_tot, nz_tot)) * 0.01,
        'ekm': np.ones((nx_tot, ny_tot, nz_tot)) * 1e-5,
        'timee': 0.0,
        'dt': 0.1,
    }

def clean_data(data_dict):
    '''
        Replace any inf or nan values with zeros in all arrays.
    
    INPUT
        data_dict - [dict]: Dictionary containing numpy arrays
        
    OUTPUT
        dict : Cleaned dictionary with inf/nan replaced by zeros
    '''
    cleaned = {}
    for key, value in data_dict.items():
        if isinstance(value, np.ndarray):
            arr = value.copy()  # Don't modify original
            arr[np.isinf(arr)] = 0.0
            arr[np.isnan(arr)] = 0.0
            cleaned[key] = arr
        else:
            cleaned[key] = value  # Keep non-array values as-is
    return cleaned

#
# MAIN FUNCTION
#
if __name__ == "__main__":
    #
    # USER INPUT DATA
    #
    nx, ny, nz = 448, 512, 192                      # Number of grid points (total)  
    exp_num = '001'                                 # Experiment number  
    nprocx, nprocy = 4, 2                           # Domain decomposition in x and y
    num_scalars = 0                                 # Number of additional scalars (typically 0 for spinup)
    #
    # PRELIMINARY CALCULATIONS
    #
    ih, jh, kh = 1, 1, 1                            # Starting indices (optional)
    ib, ie, jb, je, kb, ke = 1, nx, 1, ny, 1, nz    # Ending indices (optional)
    data_full = create_default_fields(nx, ny, nz, ih, jh, kh)
    writer = uDALESRestartWriter(ib, ie, jb, je, kb, ke, ih, jh, kh, nprocx, nprocy)
    nx_tot = nx + 2 * ih
    ny_tot = ny + 2 * jh
    nz_tot = nz + kh
    # Define the data frame that is to be written to disk
    data_partial = {
        'u0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'v0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'w0': np.zeros((nx_tot, ny_tot, nz_tot)),
        'timee': 0.0,
        'dt': 0.18,
    }
    #
    # Read the velocity field generated from GenIC
    #
    for myslice in tqdm(range(0,nx),desc="Loading slices"):
        filename = 'genic/slices/uslicedata_'+str(myslice+1)+'.dat'
        data_partial['u0'][myslice+1,1:-1, :-1] = np.loadtxt(filename)
        filename = 'genic/slices/vslicedata_'+str(myslice+1)+'.dat'
        data_partial['v0'][myslice+1,1:-1, :-1] = np.loadtxt(filename)
        filename = 'genic/slices/wslicedata_'+str(myslice+1)+'.dat'
        data_partial['w0'][myslice+1,1:-1, :-1] = np.loadtxt(filename)
    # Check for any potential NaN's and INF's
    data_partial = clean_data(data_partial)
    # Write the restart file for uDALES
    writer.write_restart_files(data_full, output_dir='./restart_files', ntrun=0, cexpnr=exp_num, nsv=0)
