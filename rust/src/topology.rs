pub struct CPUTopology {
    pub total_logical_cores: u32,
    pub p_cores: Vec<u32>,
    pub e_cores: Vec<u32>,
}

impl CPUTopology {
    pub fn detect() -> Self {
        let total = std::thread::available_parallelism()
            .map(|n| n.get() as u32)
            .unwrap_or(4);

        let mut p_cores = Vec::new();
        let mut e_cores = Vec::new();

        if total > 4 {
            let split = total / 2;
            for i in 0..split {
                p_cores.push(i);
            }
            for i in split..total {
                e_cores.push(i);
            }
        } else {
            for i in 0..total {
                p_cores.push(i);
            }
        }

        Self {
            total_logical_cores: total,
            p_cores,
            e_cores,
        }
    }

    pub fn get_all_cores_mask(&self) -> usize {
        if self.total_logical_cores >= 64 {
            usize::MAX
        } else {
            (1usize << self.total_logical_cores) - 1
        }
    }

    pub fn get_p_cores_mask(&self) -> usize {
        let mut mask = 0usize;
        for &idx in &self.p_cores {
            if idx < 64 {
                mask |= 1usize << idx;
            }
        }
        if mask == 0 { self.get_all_cores_mask() } else { mask }
    }

    pub fn get_e_cores_mask(&self) -> usize {
        let mut mask = 0usize;
        for &idx in &self.e_cores {
            if idx < 64 {
                mask |= 1usize << idx;
            }
        }
        if mask == 0 { self.get_all_cores_mask() } else { mask }
    }

    pub fn parse_affinity(&self, spec: &str) -> usize {
        match spec.trim().to_uppercase().as_str() {
            "ALL_CORES" | "ALL" => self.get_all_cores_mask(),
            "P_CORES" | "PERFORMANCE" | "CCD0" | "3D_CACHE" | "CCD0_X3D" => self.get_p_cores_mask(),
            "E_CORES" | "EFFICIENCY" | "CCD1" | "FREQUENCY" | "CCD1_FREQ" => self.get_e_cores_mask(),
            hex if hex.starts_with("0X") => {
                usize::from_str_radix(&hex[2..], 16).unwrap_or_else(|_| self.get_all_cores_mask())
            }
            dec => dec.parse::<usize>().unwrap_or_else(|_| self.get_all_cores_mask()),
        }
    }
}
