import numpy as np
from scipy.spatial.distance import squareform, pdist
from math import sqrt
import tables
import gzip
import cPickle as pickle
from sklearn.manifold import MDS, SpectralEmbedding
from sklearn.decomposition import PCA, KernelPCA
import os.path
from chordmap_base import *
from chordmap_vis import *
from sklearn.utils.arrayfuncs import min_pos

N_HARMONICS = 16
KERNEL_WIDTH = 0.001 # less than this and they are the same note
SEED = 76594

chords_i_gram_matrix = None
chords_i_dist_matrix = None

energies = 1.0/(np.arange(N_HARMONICS)+1)
base_energies = 1.0/(np.arange(N_HARMONICS)+1)
base_harm_fs = np.arange(N_HARMONICS)+1
base_fundamentals = 2.0**(np.arange(12)/12.0)
# wrap harmonics, non-log version
# note_harmonics = (((np.outer(base_fundamentals, base_harm_fs)-1.0)%1.0)+1)
# Alternatively (Thanks James Nichols for noticing)
note_harmonics = 2.0 ** (np.log2(np.outer(base_fundamentals, base_harm_fs))%1.0)

note_idx = np.arange(12, dtype="uint32")
harm_idx = np.arange(N_HARMONICS)
cross_harm_idx = cross_p_idx(N_HARMONICS, N_HARMONICS)
chord_idx = np.arange(2**12).reshape(2**12,1)

def binrotate(i, steps=1, lgth=12):
    "convenient to pack note strings to ints for performance"
    binrep = bin(i)[2:]
    pad_digits = lgth-len(binrep)
    binrep = "0"*pad_digits + binrep
    binrep = binrep[steps:]+binrep[0:steps]
    return int(binrep, base=2)

def v_kernel_fn(f1, f2, a1, a2, widths=0.01):
    """
    returns rect kernel product of points [f1, a1, f2, a2]
    NB this is not actually a cyclic kernel on [1,2], though the difference is small
    """
    return (np.abs(f1-f2)<widths)*a1*a2

def chord_notes_from_ind(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")
def chord_ind_from_notes(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")
def chord_mask_from_ind(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")
def chord_mask_from_notes(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")

#TODO: this might as well be a hdf5 table too, for consistency
def make_chord(notes):
    notes = tuple(sorted(notes))
    if not notes in _make_chord_cache:
        chord_harm_fs = note_harmonics[notes,:].flatten()
        chord_harm_energies = np.tile(base_energies, len(notes))
        _make_chord_cache[notes] = np.vstack([
            chord_harm_fs, chord_harm_energies
        ])
    return _make_chord_cache[notes]
if "_make_chord_cache" not in globals():
    if os.path.exists('_chord_map_cache_make_chords.gz'): 
        with gzip.open('_chord_map_cache_make_chords.gz', 'rb') as f:
            _make_chord_cache = pickle.load(f)
    else:
        _make_chord_cache = {}

def v_chord_product(c1, c2):
    idx = cross_p_idx(c1.shape[1], c2.shape[1])
    if idx.size==0:
        return 0.0
    f1 = c1[0,idx[0]]
    f2 = c2[0,idx[1]]
    a1 = c1[1,idx[0]]
    a2 = c2[1,idx[1]]
    return v_kernel_fn(f1, f2, a1, a2).sum()

def v_chord_dist(c1, c2):
    "construct a chord distance from the chord inner product"
    return sqrt(
        v_chord_product(c1, c1)
        - 2 * v_chord_product(c1, c2)
        + v_chord_product(c2, c2)
    )

def v_chord_product_from_chord_i_raw(ci1, ci2):
    """uncached version, for filling the cache with."""
    return v_chord_product(
        make_chord(chord_notes_from_ind(ci1)),
        make_chord(chord_notes_from_ind(ci2))
    )

def v_chord_dist2_from_chord_i(ci1, ci2):
    """construct a chord distance^2 from the chord inner product
    TODO: there is surely an optimised routine to do this in the MDS module
    would be worth using it, since this step is slow and boring
    """
    return (
        chords_i_gram_matrix[ci1, ci1]
        - 2 * chords_i_gram_matrix[ci1, ci2]
        + chords_i_gram_matrix[ci2, ci2]
    )

if os.path.exists("dists.h5"):
    with tables.open_file("dists.h5", 'r') as handle:
        chords_i_gram_matrix = handle.get_node("/", 'v_gram_matrix').read()
        chords_i_dist_matrix = handle.get_node("/", 'v_dist_matrix').read()
        chords_i_corr_matrix = handle.get_node("/", 'v_sq_corr_products').read()
        chords_i_corr_dist_matrix = handle.get_node("/", 'v_sq_corr_dists').read()
    product_power = np.diagonal(chords_i_gram_matrix)
    mean_power = np.sqrt(np.outer(product_power, product_power))
else:
    chords_i_gram_matrix = squareform(pdist(
        np.arange(2**12).reshape(2**12,1),
        v_chord_product_from_chord_i_raw
    ))
    #but wait! pdist optimised by assuming self-distance is zero
    #but this isn't a distance function! Quick!
    chords_i_gram_matrix[
        np.diag_indices_from(chords_i_gram_matrix)
    ] = [
        v_chord_product_from_chord_i_raw(i,i) for i in xrange(2**12)
    ]

    chords_i_dist_matrix = squareform(np.sqrt(pdist(
        chord_idx,
        v_chord_dist2_from_chord_i
    )))
    
    # We can also construct everything in terms of correlations...
    product_power = np.diagonal(chords_i_gram_matrix)
    mean_power = np.sqrt(np.outer(product_power, product_power))
    assert(min_pos(mean_power)>=1.0) #otherwise ... uh... double renormalization?
    chords_i_corr_matrix = chords_i_gram_matrix/np.maximum(mean_power,1)
    
    #let's do the same thing as with the product matrix but a different way because of laziness
    chords_i_corr_dist_matrix = np.zeros_like(chords_i_corr_matrix)
    for ci1 in xrange(chords_i_corr_matrix.shape[0]):
        for ci2 in xrange(ci1, chords_i_corr_matrix.shape[1]):
            if ci2 % 11 ==0:
                print ci1, ci2
            dist = sqrt(chords_i_corr_matrix[ci1, ci1]
                - 2 * chords_i_corr_matrix[ci1, ci2]
                + chords_i_corr_matrix[ci2, ci2]
            )
            chords_i_corr_dist_matrix[ci1, ci2] = dist
            chords_i_corr_dist_matrix[ci2, ci1] = dist

if not os.path.exists("dists.h5"):
    with tables.open_file("dists.h5", 'w') as handle:
        data_atom_type = tables.Float32Atom()
        filt=tables.Filters(complevel=5, complib='blosc')
        handle.create_carray("/",'v_gram_matrix',
            atom=data_atom_type, shape=chords_i_gram_matrix.shape,
            title="products",
            filters=filt)[:] = chords_i_gram_matrix
        handle.create_carray("/",'v_dist_matrix',
            atom=data_atom_type, shape=chords_i_dist_matrix.shape,
            title="dists",
            filters=filt)[:] = chords_i_dist_matrix
        handle.create_carray("/",'v_sq_corr_products',
            atom=data_atom_type, shape=chords_i_corr_matrix.shape,
            title="corrs",
            filters=filt)[:] = chords_i_corr_matrix
        handle.create_carray("/",'v_sq_corr_dists',
            atom=data_atom_type, shape=chords_i_corr_dist_matrix.shape,
            title="corr dists",
            filters=filt)[:] = chords_i_corr_dist_matrix

if not os.path.exists('_chord_map_cache_make_chords.gz'):
    with gzip.open('_chord_map_cache_make_chords.gz', 'wb') as f:
        pickle.dump(_make_chord_cache, f, protocol=2)

def get_pca(gram_matrix, n_dims=2, normalize=True):
    transformer = KernelPCA(n_components=n_dims, kernel='precomputed', eigen_solver='auto', tol=0, max_iter=None)
    transformed = transformer.fit_transform(gram_matrix) #feed the product matrix directly in for precomputed case
    if normalize:
        transformed = normalize_var(transformed)
    return transformed

def get_mds(dist_matrix,
        n_dims=3,
        metric=True,
        rotate=True,
        normalize=True,
        random_state=SEED):
    transformer = MDS(
        n_components=n_dims,
        metric=metric,
        n_init=4,
        max_iter=300,
        verbose=1,
        eps=0.001,
        n_jobs=3,
        dissimilarity='precomputed',
        random_state=random_state)
    transformed = transformer.fit_transform(dist_matrix)
    if rotate:
        # Rotate the data to a hopefully consistent orientation
        clf = PCA(n_components=n_dims)
        transformed = clf.fit_transform(transformed)
    if normalize:
        transformed = normalize_var(transformed)
    return transformed

def get_spectral_embedding_prod(gram_matrix,
        n_dims=3,
        normalize=True,
        random_state=SEED):
    #The gram matrix is already an affinity; 
    # but it has the undesirable quality of making high energy chords more similar than low energy chords
    # we normalise accordingly
    # Alternatively: RBF. See next fn
    inv_root_energy = 1.0/np.maximum(np.sqrt(np.diagonal(gram_matrix)),1)
    affinity = gram_matrix * np.outer(inv_root_energy,inv_root_energy)
    transformer = SpectralEmbedding(
        n_components=n_dims,
        affinity='precomputed',
        random_state=random_state)
    transformed = transformer.fit_transform(affinity)
    if normalize:
        transformed = normalize_var(transformed)
    return transformed

def get_spectral_embedding_dist(dist_matrix,
        n_dims=3,
        gamma=0.0625,
        normalize=True,
        random_state=SEED):
    # see previous fn
    # this needs to be 64 bit for stability
    dist_matrix = dist_matrix.astype('float64')
    affinity = np.exp(-gamma * dist_matrix * dist_matrix)
    transformer = SpectralEmbedding(
        n_components=n_dims,
        affinity='precomputed',
        random_state=random_state)
    transformed = transformer.fit_transform(affinity)
    # natural scale is dicey on this one. rescale to uni-ish variance
    var = np.var(transformed, 0)
    mean = np.mean(transformed, 0)
    if normalize:
        transformed = normalize_var(transformed)
    return transformed

def normalize_var(a, axis=None):
    """Normalise an array to unit variance"""
    return (a-np.mean(a,axis=axis, dtype='float64')
        )/np.sqrt(np.var(a,axis=axis, dtype='float64'))

def calc_and_stash(filename_base, calc):
    """convenience to calculate, serialise and return all in one line so I stop making mistakes"""
    dump_matrix_hdf("mappings/ " + filename_base + ".h5", calc) 
    dump_matrix_sc("mappings/ " + filename_base + ".scd", calc)
    return calc
#
# Three different impurity options:
#
#product with the last row (maximum chaos)
impurity_alt = normalize_var(chords_i_gram_matrix[4095,:])
dump_matrix_hdf("impurity_alt.h5", impurity_alt)

# product with chaos rescaled by own power
impurity = -(chords_i_gram_matrix[4095,:]/product_power)
impurity[0] = np.mean(impurity[1:]) #because of null entry
impurity = normalize_var(impurity)
impurity[0] = 0 #because of null entry
dump_matrix_hdf("impurity.h5", impurity)
#I'm not sure which is better, but since they have a correlation of 0.82 it may not matter

impurity_lin = -np.sqrt(chords_i_gram_matrix[4095,:]/product_power)
impurity_lin[0] = np.mean(impurity_lin[1:]) #because of null entry
impurity_lin = normalize_var(impurity_lin)
impurity_lin[0] = 0 #because of null entry
dump_matrix_hdf("impurity_lin.h5", impurity_lin)

kpca_2 = calc_and_stash("kpca_2", get_pca(chords_i_gram_matrix, n_dims=2))
kpca_3 = calc_and_stash("kpca_3", get_pca(chords_i_gram_matrix, n_dims=3))
lin_mds_2 = calc_and_stash("lin_mds_2", get_mds(chords_i_gram_matrix, n_dims=2))
lin_mds_3 = calc_and_stash("lin_mds_3", get_mds(chords_i_gram_matrix, n_dims=3))
spectral_embed_prod_2 = calc_and_stash("spectral_embed_prod_2", get_spectral_embedding_prod(chords_i_gram_matrix, n_dims=2))
spectral_embed_prod_3 = calc_and_stash("spectral_embed_prod_3", get_spectral_embedding_prod(chords_i_gram_matrix, n_dims=3))
spectral_embed_prod_4 = calc_and_stash("spectral_embed_prod_4", get_spectral_embedding_prod(chords_i_gram_matrix, n_dims=3))
spectral_embed_dist_2 = calc_and_stash("spectral_embed_dist_2", get_spectral_embedding_dist(chords_i_dist_matrix, n_dims=2))
spectral_embed_dist_3 = calc_and_stash("spectral_embed_dist_3", get_spectral_embedding_dist(chords_i_dist_matrix, n_dims=3))
spectral_embed_dist_4 = calc_and_stash("spectral_embed_dist_4", get_spectral_embedding_dist(chords_i_dist_matrix, n_dims=4))
nonlin_mds_2 = calc_and_stash("nonlin_mds_2", get_mds(chords_i_dist_matrix, n_dims=2, metric=False, rotate=False))
nonlin_mds_3 = calc_and_stash("nonlin_mds_3", get_mds(chords_i_dist_matrix, n_dims=3, metric=False, rotate=False))

##########correlation ones
kpca_corr_2 = calc_and_stash("kpca_corr_2", get_pca(chords_i_gram_matrix, n_dims=2))
kpca_corr_3 = calc_and_stash("kpca_corr_3", get_pca(chords_i_gram_matrix, n_dims=3))
lin_mds_corr_2 = calc_and_stash("lin_mds_corr_2", get_mds(chords_i_gram_matrix, n_dims=2))
lin_mds_corr_3 = calc_and_stash("lin_mds_corr_3", get_mds(chords_i_gram_matrix, n_dims=3))
spectral_embed_prod_corr_2 = calc_and_stash("spectral_embed_prod_corr_2", get_spectral_embedding_prod(chords_i_gram_matrix, n_dims=2))
spectral_embed_prod_corr_3 = calc_and_stash("spectral_embed_prod_corr_3", get_spectral_embedding_prod(chords_i_gram_matrix, n_dims=3))
spectral_embed_prod_corr_4 = calc_and_stash("spectral_embed_prod_corr_4", get_spectral_embedding_prod(chords_i_gram_matrix, n_dims=3))
spectral_embed_dist_corr_2 = calc_and_stash("spectral_embed_dist_corr_2", get_spectral_embedding_dist(chords_i_dist_matrix, n_dims=2))
spectral_embed_dist_corr_3 = calc_and_stash("spectral_embed_dist_corr_3", get_spectral_embedding_dist(chords_i_dist_matrix, n_dims=3))
spectral_embed_dist_corr_4 = calc_and_stash("spectral_embed_dist_corr_4", get_spectral_embedding_dist(chords_i_dist_matrix, n_dims=4))
nonlin_mds_corr_2 = calc_and_stash("nonlin_mds_corr_2", get_mds(chords_i_dist_matrix, n_dims=2, metric=False, rotate=False))
nonlin_mds_corr_3 = calc_and_stash("nonlin_mds_corr_3", get_mds(chords_i_dist_matrix, n_dims=3, metric=False, rotate=False))

###################Viz
#chordmap_vis.plot_2d(spectral_embed_prod_corr_2)
#chordmap_vis.plot_2d(spectral_embed_dist_corr_2) #flat saturn. flaturn.
#chordmap_vis.plot_3d(spectral_embed_prod_corr_3) #radial rainbow ball
#chordmap_vis.plot_3d(spectral_embed_dist_corr_3) #weird striated honeycomb
#chordmap_vis.plot_3d(spectral_embed_prod_corr_4) #radial rainbow ball
#chordmap_vis.plot_3d(spectral_embed_dist_corr_4) #weird striated honeycomb

def decache():
    "nasty hack for loading analysis from cache"
    for basename in [
        "kpca_2",
        "kpca_3",
        "kpca_corr_2",
        "kpca_corr_3",
        "lin_mds_2",
        "lin_mds_3",
        "lin_mds_4",
        "lin_mds_corr_2",
        "lin_mds_corr_3",
        "nonlin_mds_2",
        "nonlin_mds_3",
        "nonlin_mds_corr_2",
        "nonlin_mds_corr_3",
        "spectral_embed_dist_2",
        "spectral_embed_dist_3",
        "spectral_embed_dist_4",
        "spectral_embed_dist_corr_2",
        "spectral_embed_dist_corr_3",
        "spectral_embed_dist_corr_4",
        "spectral_embed_prod_2",
        "spectral_embed_prod_3",
        "spectral_embed_prod_4",
        "spectral_embed_prod_corr_2",
        "spectral_embed_prod_corr_3",
        "spectral_embed_prod_corr_4",
        "impurity",
        "impurity_alt",
        "impurity_lin",
    ]:
        globals()[basename] = load_matrix_hdf("mappings/" + basename + ".h5")
        
# Interesting exemplars:
# conical! impurity is already captured by radius:
plot_3d(np.hstack([lin_mds_corr_2, impurity_alt.reshape(-1,1)])) 
#"handerchief" manifolds
plot_3d(np.hstack([lin_mds_2, impurity_alt.reshape(-1,1)]))
plot_3d(np.hstack([spectral_embed_dist_2, impurity_alt.reshape(-1,1)]))
#diamond manifold: 3rd axis adds nothing
plot_3d(np.hstack([kpca_2, impurity_alt.reshape(-1,1)]))
# OTOH, this is a sphere no matter how you look at it.... true 4d?
plot_3d(np.hstack([kpca_3, impurity_alt.reshape(-1,1)]))
# cones:
plot_3d(np.hstack([spectral_embed_prod_2, impurity_alt.reshape(-1,1)]))
plot_3d(np.hstack([spectral_embed_dist_corr_2, impurity_alt.reshape(-1,1)]))
plot_3d(np.hstack([spectral_embed_prod_corr_2, impurity_alt.reshape(-1,1)]))
#4d cone
plot_3d(np.hstack([spectral_embed_dist_3, impurity_lin.reshape(-1,1)]))

# can stash them lik, e.g.
dump_matrix_sc("mappings/spectral_embed_prod_corr_2_impurity_alt.scd", np.hstack([spectral_embed_prod_corr_2, impurity_alt.reshape(-1,1)])) 
